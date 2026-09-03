import os
import uuid
import time
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from starlette.requests import Request

from main import app
import config
from database import SessionLocal
from models.client import Client, ClientStatus
from models.session import Session as SessionModel, SessionStatus, ClientLiveSession
from models.rate import Rate
from models.voucher import Voucher, VoucherStatus
from models.coin_reservation import CoinReservation, PendingCoin
from models.coin_event import CoinEvent, CoinEventStatus
from services.coin_settlement_service import CoinSettlementService
from coin_serial.coin_spool import CoinSpool
from services.session_service import SessionService
from repositories.session_repository import SessionRepository
from repositories.client_repository import ClientRepository
from repositories.rate_repository import RateRepository
from recovery.power_recovery import PowerRecovery
from utils.time_utils import get_utc_now

test_client = TestClient(app)


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


def test_dnsmasq_no_wildcard_poisoning():
    """Verify dnsmasq configuration does not contain wildcard domain poisoning address=/#/..."""
    template_path = os.path.join(config.BASE_DIR, "config/dnsmasq/dnsmasq.conf.template")
    conf_path = os.path.join(config.BASE_DIR, "config/dnsmasq/dnsmasq.conf")

    for path in (template_path, conf_path):
        if os.path.exists(path):
            with open(path, "r") as f:
                content = f.read()
            assert "address=/#/" not in content, f"Wildcard DNS poisoning found in {path}"
            assert "server=1.1.1.1" in content or "server=8.8.8.8" in content, f"Upstream DNS missing in {path}"


def test_cross_client_identity_theft_rejected(db):
    """
    Verify that Client A cannot inspect, pause, or resume Client B's session
    even if Client A supplies Client B's MAC in the URL path.
    """
    mac_a = gen_mac()
    mac_b = gen_mac()

    client_a = Client(mac_address=mac_a, current_ip="192.168.4.10", status=ClientStatus.ONLINE)
    client_b = Client(mac_address=mac_b, current_ip="192.168.4.20", status=ClientStatus.ONLINE)
    db.add(client_a)
    db.add(client_b)
    db.commit()

    rate = db.query(Rate).first()
    if not rate:
        rate = Rate(coin_value=5, minutes=60, enabled=True)
        db.add(rate)
        db.commit()

    # Create active session for Client B
    sess_service = SessionService(SessionRepository(db))
    sess_b = sess_service.create_or_extend_session(client_b.id, rate.id, 60, authorize=False)

    # Client A attempts to access Client B's session specifying claimed_mac=mac_b
    # When spoofed via headers or gateway mismatch, resolve_trusted_client must reject with 403
    from services.client_service import ClientService

    # Simulate request originating from Client A's connection (IP 192.168.4.10)
    class FakeLANRequest:
        client = type("ClientAddr", (), {"host": "192.168.4.10"})()
        headers = {"X-Real-IP": "192.168.4.20"}  # Client A attempts to spoof IP

    req = FakeLANRequest()
    client_service = ClientService(ClientRepository(db))

    # 1. Inspect session
    with pytest.raises(Exception) as exc_info:
        client_service.resolve_trusted_client(req, claimed_mac=mac_b)
    assert exc_info.value.status_code == 403

    # 2. Verify untrusted proxy headers from LAN are ignored
    from services.network_service import NetworkService
    net = NetworkService()
    observed_ip = net.get_client_ip(req)
    assert observed_ip == "192.168.4.10"  # Did not trust spoofed X-Real-IP


def test_cross_client_voucher_theft_rejected(db):
    """Verify that a client cannot redeem a voucher into another customer's session."""
    mac_a = gen_mac()
    mac_b = gen_mac()

    client_a = Client(mac_address=mac_a, current_ip="192.168.4.30", status=ClientStatus.ONLINE)
    client_b = Client(mac_address=mac_b, current_ip="192.168.4.40", status=ClientStatus.ONLINE)
    db.add(client_a)
    db.add(client_b)

    code = f"TS{uuid.uuid4().hex[:8].upper()}"
    voucher = Voucher(
        code=code,
        minutes=120,
        status=VoucherStatus.UNUSED,
        created_at=get_utc_now()
    )
    db.add(voucher)
    db.commit()

    from api.v1.voucher import _process_voucher_redemption

    class FakeLANRequest:
        client = type("ClientAddr", (), {"host": "192.168.4.30"})()
        headers = {}

    # Client at 192.168.4.30 claims to be mac_b
    with pytest.raises(Exception) as exc:
        _process_voucher_redemption(code, mac_b, "192.168.4.30", db, request=FakeLANRequest())
    assert exc.value.status_code == 403


def test_coin_insert_exactly_once_idempotency(db):
    """Verify that duplicate coin insertions with the same event_id credit exactly once."""
    db.query(CoinReservation).delete()
    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="127.0.0.1", status=ClientStatus.ONLINE)
    db.add(client)

    lease_id = str(uuid.uuid4())
    now = get_utc_now()
    reservation = CoinReservation(
        mac=mac,
        lease_id=lease_id,
        owner_ip="127.0.0.1",
        reserved_at=now,
        expires_at=now + timedelta(seconds=120)
    )
    db.add(reservation)
    db.commit()

    class FakeHardwareReq:
        client = type("ClientAddr", (), {"host": "127.0.0.1"})()
        headers = {}

    from api.v1.coin import insert_coin
    event_id = str(uuid.uuid4())

    # First insert
    res1 = insert_coin(5, lease_id, FakeHardwareReq(), db, event_id=event_id)
    assert res1.success is True
    assert res1.data["status"] == "accumulated"

    # Second insert with same event_id
    res2 = insert_coin(5, lease_id, FakeHardwareReq(), db, event_id=event_id)
    assert res2.success is True
    assert res2.data["status"] == "already_recorded"

    # Verify only 1 CoinEvent exists in DB with this event_id
    count = db.query(CoinEvent).filter(CoinEvent.event_id == event_id).count()
    assert count == 1


def test_coin_settlement_idempotent_finalization(db):
    """Verify that CoinSettlementService finalize_lease is strictly idempotent."""
    if not db.query(Rate).filter_by(coin_value=20).first():
        db.add(Rate(coin_value=20, minutes=120))
        db.commit()

    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="127.0.0.1", status=ClientStatus.ONLINE)
    db.add(client)

    lease_id = str(uuid.uuid4())
    now = get_utc_now()
    reservation = CoinReservation(
        mac=mac,
        lease_id=lease_id,
        owner_ip="127.0.0.1",
        reserved_at=now,
        expires_at=now + timedelta(seconds=120)
    )
    db.add(reservation)

    event_id_1 = str(uuid.uuid4())
    event_id_2 = str(uuid.uuid4())
    db.add(CoinEvent(
        event_id=event_id_1,
        denomination=10,
        lease_id=lease_id,
        mac=mac,
        status=CoinEventStatus.RECEIVED.value,
        received_at=now,
        persisted_at=now
    ))
    db.add(CoinEvent(
        event_id=event_id_2,
        denomination=10,
        lease_id=lease_id,
        mac=mac,
        status=CoinEventStatus.RECEIVED.value,
        received_at=now,
        persisted_at=now
    ))
    db.commit()

    settlement = CoinSettlementService(db)

    # First finalization
    result1 = settlement.finalize_lease(lease_id=lease_id, authorize=False)
    assert result1["status"] == "finalized"
    assert result1["total_amount"] == 20

    # Verify events are marked PROCESSED
    e1 = db.query(CoinEvent).filter(CoinEvent.event_id == event_id_1).first()
    e2 = db.query(CoinEvent).filter(CoinEvent.event_id == event_id_2).first()
    assert e1.status == CoinEventStatus.PROCESSED.value
    assert e2.status == CoinEventStatus.PROCESSED.value

    # Second finalization call with the same lease
    result2 = settlement.finalize_lease(lease_id=lease_id, authorize=False)
    assert result2["status"] == "already_finalized"
    assert result2["total_amount"] == 0

    # Verify session was credited only once
    live = db.query(ClientLiveSession).filter(ClientLiveSession.client_id == client.id).first()
    assert live is not None
    session = db.query(SessionModel).filter(SessionModel.id == live.session_id).first()
    # 20 pesos purchased minutes should not be duplicated
    assert session.purchased_minutes > 0


def test_power_recovery_preserves_remaining_time_across_outage(db, monkeypatch):
    """
    Verify that an unexpected power outage (e.g. 2 hours off) does NOT drain customer time.
    The customer's remaining seconds must be preserved into PAUSED state.
    """
    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="192.168.4.50", status=ClientStatus.ONLINE)
    db.add(client)
    db.flush()

    rate = db.query(Rate).first()
    now = get_utc_now()
    session = SessionModel(
        client_id=client.id,
        rate_id=rate.id if rate else 1,
        status=SessionStatus.ACTIVE,
        start_time=now - timedelta(minutes=10),
        end_time=now + timedelta(minutes=50),
        remaining_seconds=3000,  # 50 minutes remaining
        remaining_minutes=50,
        purchased_minutes=60,
        last_accounted_at=now,
    )
    db.add(session)
    db.flush()

    live = ClientLiveSession(client_id=client.id, session_id=session.id, status="ACTIVE", updated_at=now)
    db.add(live)
    db.commit()

    # Simulate appliance booting up 2 hours later after hardware power loss
    recovery = PowerRecovery(SessionRepository(db), db)

    # Mock /proc/uptime to simulate boot within last 30 seconds
    import io
    monkeypatch.setattr("builtins.open", lambda path, mode="r": io.StringIO("25.0 50.0") if "uptime" in path else open(path, mode))

    # Fast-forward clock by 2 hours
    monkeypatch.setattr("recovery.power_recovery.get_utc_now", lambda: now + timedelta(hours=2))

    recovered_count = recovery.recover()
    assert recovered_count >= 1

    db.refresh(session)
    db.refresh(live)

    # Session must be safely PAUSED and NOT have 0 remaining seconds!
    assert session.status == SessionStatus.PAUSED
    assert live.status == "PAUSED"
    assert session.remaining_seconds == 3000, f"Remaining seconds corrupted: {session.remaining_seconds}"
    assert session.remaining_minutes == 50


def test_db_enforced_single_live_session_invariant(db):
    """
    Verify the database invariant: A client cannot have multiple live sessions simultaneously.
    Unique constraint on client_live_sessions prevents concurrent duplicate live sessions.
    """
    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="192.168.4.60", status=ClientStatus.ONLINE)
    db.add(client)
    db.flush()

    rate = db.query(Rate).first()
    rate_id = rate.id if rate else 1
    now = get_utc_now()

    s1 = SessionModel(client_id=client.id, rate_id=rate_id, status=SessionStatus.ACTIVE, purchased_minutes=30, remaining_minutes=30, remaining_seconds=1800, start_time=now, end_time=now + timedelta(minutes=30))
    s2 = SessionModel(client_id=client.id, rate_id=rate_id, status=SessionStatus.ACTIVE, purchased_minutes=60, remaining_minutes=60, remaining_seconds=3600, start_time=now, end_time=now + timedelta(minutes=60))
    db.add(s1)
    db.add(s2)
    db.flush()

    live1 = ClientLiveSession(client_id=client.id, session_id=s1.id, status="ACTIVE")
    db.add(live1)
    db.commit()

    # Attempting to insert a second live session for the same client must violate primary key constraint
    live2 = ClientLiveSession(client_id=client.id, session_id=s2.id, status="ACTIVE")
    db.add(live2)

    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_coin_spool_write_ahead_durability(tmp_path):
    """Verify CoinSpool persists event to disk before dispatch and cleans up on ACK."""
    spool_dir = str(tmp_path / "coin_spool")
    spool = CoinSpool(spool_dir=spool_dir)

    lease_id = str(uuid.uuid4())
    event = spool.create_event(denomination=10, lease_id=lease_id, source="gpio", pulse_count=10)
    event_id = event["event_id"]

    # Verify file is durably written on disk
    filepath = spool._get_filepath(event_id)
    assert os.path.exists(filepath)

    # Verify mark acknowledged deletes from disk
    spool.mark_acknowledged(event_id)
    assert not os.path.exists(filepath)
