import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from main import app
import config
from database import SessionLocal
from models.client import Client, ClientStatus
from models.session import Session as SessionModel, SessionStatus
from models.rate import Rate
from models.voucher import Voucher, VoucherStatus
from services.session_service import SessionService
from repositories.session_repository import SessionRepository
from services.network_service import NetworkService
from services.firewall_service import NftablesFirewallDriver, FirewallService
from utils.auth import create_access_token
from utils.time_utils import get_utc_now

test_client = TestClient(app)


def gen_random_mac():
    raw = uuid.uuid4().hex[:12].upper()
    return ":".join(raw[i:i+2] for i in range(0, 12, 2))


@pytest.fixture(autouse=True)
def mock_firewall(mocker):
    mocker.patch.object(FirewallService, "authorize", return_value=None)
    mocker.patch.object(FirewallService, "remove", return_value=None)


@pytest.fixture
def admin_token():
    return create_access_token("admin")


def test_issue1_paused_session_time_preservation():
    """Verify that pausing, extending, and resuming a session preserves exact duration without corruption."""
    db = SessionLocal()
    try:
        mac = gen_random_mac()
        client_obj = Client(mac_address=mac, status=ClientStatus.OFFLINE)
        db.add(client_obj)
        db.flush()

        rate_obj = db.query(Rate).filter(Rate.enabled.is_(True)).first()
        if not rate_obj:
            rate_obj = Rate(coin_value=1, minutes=20, enabled=True)
            db.add(rate_obj)
            db.commit()

        session_repo = SessionRepository(db)
        service = SessionService(session_repo)

        # Create active session of 60 minutes
        sess = service.create_or_extend_session(client_obj.id, rate_obj.id, 60, authorize=False)
        db.commit()
        client_id = client_obj.id
        rate_id = rate_obj.id
        assert sess.status == SessionStatus.ACTIVE
    finally:
        db.close()

    # Pause session via API
    resp_pause = test_client.post(f"/api/v1/session/pause/{mac}")
    assert resp_pause.status_code == 200
    assert resp_pause.json()["success"] is True

    # Verify PAUSED status in DB
    db2 = SessionLocal()
    try:
        session_repo2 = SessionRepository(db2)
        sess_paused = session_repo2.get_paused_session_by_client_id(client_id)
        assert sess_paused is not None
        assert sess_paused.remaining_seconds is not None
        assert sess_paused.remaining_seconds > 3500  # Should be close to 3600 seconds
        assert sess_paused.remaining_minutes == sess_paused.remaining_seconds // 60

        # Extend paused session by 20 minutes
        service2 = SessionService(session_repo2)
        sess_ext = service2.create_or_extend_session(client_id, rate_id, 20, authorize=False)
        db2.commit()

        assert sess_ext.status == SessionStatus.ACTIVE
        total_remaining = (sess_ext.end_time - get_utc_now()).total_seconds()
        assert total_remaining > 4700  # ~80 minutes, NOT 21 seconds/minutes!
    finally:
        db2.close()



def test_issue2_test_coin_endpoint_disabled_in_production():
    """Verify /test/{mac}/{value} is NOT accessible when config.DEBUG=False and config.ENVIRONMENT='production'."""
    old_debug = config.DEBUG
    old_env = config.ENVIRONMENT
    try:
        config.DEBUG = False
        config.ENVIRONMENT = "production"
        mac = gen_random_mac()
        resp = test_client.post(f"/api/v1/coin/test/{mac}/10")
        assert resp.status_code in (404, 405)
    finally:
        config.DEBUG = old_debug
        config.ENVIRONMENT = old_env


def test_issue3_no_session_hijacking_on_shared_ip():
    """Verify that visiting /api/v1/client on a shared IP does NOT hijack another client's active session."""
    db = SessionLocal()
    try:
        mac1 = gen_random_mac()
        mac2 = gen_random_mac()
        client1 = Client(mac_address=mac1, current_ip="10.0.0.50", status=ClientStatus.ONLINE)
        client2 = Client(mac_address=mac2, current_ip=None, status=ClientStatus.OFFLINE)
        rate = db.query(Rate).filter(Rate.enabled.is_(True)).first()
        if not rate:
            rate = Rate(coin_value=1, minutes=20, enabled=True)
            db.add(rate)

        db.add_all([client1, client2])
        db.commit()

        session_repo = SessionRepository(db)
        sess1 = session_repo.create_session(client1.id, rate.id, 120)

        # Client 2 connects from same IP 10.0.0.50
        headers = {"X-Real-IP": "10.0.0.50"}
        resp = test_client.get("/api/v1/client", headers=headers)
        assert resp.status_code == 200

        db.refresh(sess1)
        # Session MUST remain with Client 1
        assert sess1.client_id == client1.id
    finally:
        db.close()


def test_issue4_real_client_ip_resolution():
    """Verify NetworkService.get_client_ip extracts X-Real-IP and X-Forwarded-For properly."""
    net_service = NetworkService()

    class DummyRequest:
        def __init__(self, headers, client_host="127.0.0.1"):
            self.headers = headers
            class ClientInfo:
                host = client_host
            self.client = ClientInfo()

    req1 = DummyRequest({"X-Real-IP": "192.168.1.100"})
    assert net_service.get_client_ip(req1) == "192.168.1.100"

    req2 = DummyRequest({"X-Forwarded-For": "10.0.0.200, 127.0.0.1"})
    assert net_service.get_client_ip(req2) == "10.0.0.200"


def test_issue5_firewall_error_handling(mocker):
    """Verify NftablesFirewallDriver.authorize raises RuntimeError if nft command fails."""
    driver = NftablesFirewallDriver()
    mocker.patch("subprocess.run", return_value=mocker.Mock(returncode=1, stderr="Operation not permitted"))
    with pytest.raises(RuntimeError) as exc_info:
        driver.authorize("10.0.0.100")
    assert "Operation not permitted" in str(exc_info.value)


def test_issue7_coin_debouncing():
    """Verify debouncer works at raw packet level without discarding valid distinct packets."""
    from coin_serial.debounce import Debouncer
    debouncer = Debouncer()

    # First packet allowed
    assert debouncer.allow("PULSES:1") is True
    # Immediate duplicate within debounce window blocked
    assert debouncer.allow("PULSES:1") is False

    # Different packet allowed
    assert debouncer.allow("PULSES:5") is True


def test_issue10_voucher_audit_preservation(admin_token):
    """Verify deleting a USED voucher returns 400 Bad Request to preserve financial audit trail."""
    from utils.auth import generate_csrf_token
    csrf_token = generate_csrf_token()
    db = SessionLocal()
    try:
        voucher = Voucher(
            code=f"AUDIT_{uuid.uuid4().hex[:8].upper()}",
            minutes=60,
            status=VoucherStatus.USED,
            used_at=get_utc_now()
        )
        db.add(voucher)
        db.commit()
        db.refresh(voucher)
        voucher_id = voucher.id

        test_client.cookies.set("admin_token", admin_token)
        test_client.cookies.set("csrf_token", csrf_token)
        resp = test_client.delete(
            f"/api/admin/vouchers/{voucher_id}",
            headers={"X-CSRF-Token": csrf_token},
        )
        assert resp.status_code == 400
        assert "Cannot delete a used voucher" in resp.json()["detail"]
    finally:
        db.close()
