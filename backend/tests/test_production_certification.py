import os
import uuid
import threading
import pytest
from datetime import datetime, timedelta
import config
from database import SessionLocal
from models.client import Client, ClientStatus
from models.session import Session as SessionModel, SessionStatus, ClientLiveSession
from models.rate import Rate
from models.voucher import Voucher, VoucherStatus
from models.sale import Sale
from models.coin_reservation import CoinReservation
from models.coin_event import CoinEvent, CoinEventStatus
from models.network_authorization import NetworkAuthorization, NetworkAuthState
from services.firewall_service import FirewallService, MockFirewallDriver
from services.firewall_reconciler import FirewallReconciler
from services.session_service import SessionService
from services.coin_settlement_service import CoinSettlementService
from repositories.session_repository import SessionRepository
from recovery.power_recovery import PowerRecovery
from scheduler.jobs import expire_sessions, sync_firewall
from utils.time_utils import get_utc_now


def gen_mac():
    raw = uuid.uuid4().hex[:12].upper()
    return ":".join(raw[i:i+2] for i in range(0, 12, 2))


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_concurrent_voucher_redemption_race(db, monkeypatch):
    """
    10 concurrent threads attempt to redeem the exact same unused voucher simultaneously.
    Invariant: Exactly 1 succeeds, 9 are rejected, preventing double crediting.
    """
    from api.v1.voucher import _process_voucher_redemption

    monkeypatch.setattr(config, "FIREWALL_DRIVER", "mock")
    voucher_code = f"RACE{uuid.uuid4().hex[:8].upper()}"
    voucher = Voucher(
        code=voucher_code,
        minutes=60,
        status=VoucherStatus.UNUSED,
        created_at=get_utc_now(),
    )
    db.add(voucher)
    db.commit()

    results = []

    def attempt_redeem():
        thread_db = SessionLocal()
        thread_mac = gen_mac()
        thread_ip = "127.0.0.1"
        client = Client(mac_address=thread_mac, current_ip=thread_ip, status=ClientStatus.ONLINE)
        thread_db.add(client)
        thread_db.commit()

        class FakeReq:
            client = type("ClientAddr", (), {"host": "testclient"})()
            headers = {}

        try:
            res = _process_voucher_redemption(voucher_code, thread_mac, thread_ip, thread_db, request=FakeReq())
            results.append(("SUCCESS", res))
        except Exception as exc:
            results.append(("FAILED", getattr(exc, "status_code", 500)))
        finally:
            thread_db.close()

    threads = [threading.Thread(target=attempt_redeem) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [r for r in results if r[0] == "SUCCESS"]
    failures = [r for r in results if r[0] == "FAILED"]

    assert len(successes) == 1, f"Expected exactly 1 voucher redemption success, got {len(successes)}"
    assert len(failures) == 9, f"Expected 9 voucher redemption failures, got {len(failures)}"

    db.expire_all()
    reloaded_voucher = db.query(Voucher).filter(Voucher.code == voucher_code).first()
    assert reloaded_voucher.status == VoucherStatus.USED


def test_concurrent_coin_finalization_races(db):
    """
    Two concurrent threads attempt to finalize the exact same coin lease at the same millisecond.
    Invariant: Exactly-once crediting with 0 lost coins and 0 double credits.
    """
    db.query(CoinReservation).delete()
    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="192.168.4.150", status=ClientStatus.ONLINE)
    db.add(client)

    lease_id = str(uuid.uuid4())
    now = get_utc_now()
    reservation = CoinReservation(
        mac=mac,
        lease_id=lease_id,
        owner_ip="192.168.4.150",
        reserved_at=now,
        expires_at=now + timedelta(seconds=60)
    )
    db.add(reservation)

    event_id = str(uuid.uuid4())
    event = CoinEvent(
        event_id=event_id,
        lease_id=lease_id,
        mac=mac,
        denomination=5,
        pulse_count=5,
        status=CoinEventStatus.RECEIVED.value,
        received_at=now
    )
    db.add(event)
    db.commit()

    results = []
    mock_fw = FirewallService()
    mock_fw.driver = MockFirewallDriver()

    def finalize_thread():
        thread_db = SessionLocal()
        try:
            sess_svc = SessionService(SessionRepository(thread_db), firewall_service=mock_fw)
            svc = CoinSettlementService(thread_db, session_service=sess_svc)
            res = svc.finalize_lease(lease_id=lease_id, mac=mac)
            results.append(res)
        finally:
            thread_db.close()

    t1 = threading.Thread(target=finalize_thread)
    t2 = threading.Thread(target=finalize_thread)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    statuses = [r.get("status") for r in results]
    assert "finalized" in statuses
    # Total credited amount across threads must equal exactly 5 pesos
    total_credited = sum(r.get("total_amount", 0) for r in results)
    assert total_credited == 5

    # Total recorded sales must equal exactly 1 sale for 5 pesos
    sess = db.query(SessionModel).filter(SessionModel.client_id == client.id).first()
    assert sess is not None
    sales = db.query(Sale).filter(Sale.session_id == sess.id).all()
    assert len(sales) == 1
    assert sales[0].amount == 5


def test_session_expiration_firewall_revocation(db):
    """
    A customer session expires while traffic is active.
    Invariant: Firewall authorization state is immediately updated to BLOCKED,
    and firewall reconciler flushes the kernel set element.
    """
    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="192.168.4.160", status=ClientStatus.ONLINE)
    db.add(client)
    db.commit()

    rate = db.query(Rate).first()
    if not rate:
        rate = Rate(coin_value=1, minutes=20, enabled=True)
        db.add(rate)
        db.commit()

    mock_driver = MockFirewallDriver()
    firewall = FirewallService()
    firewall.driver = mock_driver

    sess_service = SessionService(SessionRepository(db), firewall_service=firewall)
    session = sess_service.create_or_extend_session(client.id, rate.id, 20, authorize=True)

    assert (client.current_ip, mac.lower()) in mock_driver.active_pairs

    # Simulate expiration: advance end_time and remaining_seconds into past
    now = get_utc_now()
    session.end_time = now - timedelta(seconds=10)
    session.remaining_seconds = 0
    session.remaining_minutes = 0
    db.commit()

    # Run scheduler expiration job
    expire_sessions()

    # Verify database network authorization desired state updated to BLOCKED
    auth = db.query(NetworkAuthorization).filter(NetworkAuthorization.client_id == client.id).first()
    assert auth.desired_state == NetworkAuthState.BLOCKED.value

    # Reconciler syncs kernel state
    reconciler = FirewallReconciler(firewall_service=firewall)
    reconciler.reconcile_once(db)

    # Active pair must be evicted
    assert (client.current_ip, mac.lower()) not in mock_driver.active_pairs


def test_power_loss_recovery_checkpoint_preservation(db):
    """
    Appliance loses power while sessions are active.
    2 hours later appliance boots.
    Invariant: Customer's unconsumed purchased time is preserved in PAUSED state.
    Power downtime does not drain remaining seconds.
    """
    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="192.168.4.170", status=ClientStatus.ONLINE)
    db.add(client)
    db.commit()

    rate = db.query(Rate).first()
    rate_id = rate.id if rate else 1

    # Session started with 1800 seconds (30 minutes).
    # Checkpointed with 1500 seconds remaining before sudden power off.
    now = get_utc_now()
    session = SessionModel(
        client_id=client.id,
        rate_id=rate_id,
        status=SessionStatus.ACTIVE,
        purchased_minutes=30,
        remaining_minutes=25,
        remaining_seconds=1500,
        start_time=now - timedelta(hours=2, minutes=5),
        end_time=now - timedelta(hours=1, minutes=35),  # wall-clock ended during outage!
        last_accounted_at=now - timedelta(hours=2),
    )
    db.add(session)
    db.flush()

    live = ClientLiveSession(client_id=client.id, session_id=session.id, status=SessionStatus.ACTIVE.value)
    db.add(live)
    db.commit()

    # Power recovery runs on boot
    recovered_count = PowerRecovery(SessionRepository(db), db).recover(force=True)
    assert recovered_count >= 1

    db.refresh(session)
    assert session.status == SessionStatus.PAUSED
    assert session.remaining_seconds == 1500, "Remaining seconds must NOT be drained by power outage downtime!"
    assert session.remaining_minutes == 25


def test_anti_spoofing_mismatched_pair_isolation():
    """
    Anti-spoofing binding:
    - Authorized pair is (IP_A, MAC_A).
    - Attacker with (IP_A, MAC_B) or (IP_B, MAC_A) fails lookup in authorized set.
    """
    driver = MockFirewallDriver()
    driver.authorize("192.168.4.50", "AA:BB:CC:DD:EE:01")

    active = driver.get_active_elements()
    assert ("192.168.4.50", "aa:bb:cc:dd:ee:01") in active

    # IP match with wrong MAC
    assert ("192.168.4.50", "aa:bb:cc:dd:ee:99") not in active

    # MAC match with wrong IP
    assert ("192.168.4.99", "aa:bb:cc:dd:ee:01") not in active


def test_continuous_reconciler_rogue_and_dropped_correction(db):
    """
    Verify FirewallReconciler automatically evicts rogue unrecorded allow rules
    and restores missing legitimate authorizations within a single cycle.
    """
    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="192.168.4.180", status=ClientStatus.ONLINE)
    db.add(client)
    db.commit()

    now = get_utc_now()
    legit_auth = NetworkAuthorization(
        client_id=client.id,
        mac_address=mac,
        ip_address=client.current_ip,
        desired_state=NetworkAuthState.AUTHORIZED.value,
        applied_state=NetworkAuthState.AUTHORIZED.value,
        created_at=now,
        updated_at=now,
    )
    db.add(legit_auth)
    db.commit()

    mock_driver = MockFirewallDriver()
    # Rogue entry in kernel
    rogue_pair = ("192.168.4.222", "66:77:88:99:00:11")
    mock_driver.active_pairs.add((rogue_pair[0], rogue_pair[1].lower()))

    # Legitimate pair missing from kernel
    assert (client.current_ip, mac.lower()) not in mock_driver.active_pairs

    firewall = FirewallService()
    firewall.driver = mock_driver

    reconciler = FirewallReconciler(firewall_service=firewall)
    metrics = reconciler.reconcile_once(db)

    # Reconciler must evict rogue and restore legitimate
    assert (rogue_pair[0], rogue_pair[1].lower()) not in mock_driver.active_pairs
    assert (client.current_ip, mac.lower()) in mock_driver.active_pairs
    assert metrics["stale_allow_count"] >= 1
    assert metrics["false_deny_count"] >= 1
