import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from main import app
import config
from database import SessionLocal
from models.voucher import Voucher, VoucherStatus
from models.client import Client, ClientStatus
from models.rate import Rate
from models.sale import Sale, PaymentMethod
from utils.auth import create_access_token
from services.firewall_service import FirewallService

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_firewall(mocker):
    mocker.patch.object(FirewallService, "authorize", return_value=None)
    mocker.patch.object(FirewallService, "remove", return_value=None)


@pytest.fixture
def admin_token():

    return create_access_token("admin")


@pytest.fixture
def setup_db_data():
    db = SessionLocal()
    try:
        # Create test client
        test_client = db.query(Client).filter(Client.mac_address == "00:11:22:33:44:55").first()
        if not test_client:
            test_client = Client(
                mac_address="00:11:22:33:44:55",
                current_ip="10.0.0.100",
                status=ClientStatus.OFFLINE,
            )
            db.add(test_client)

        # Create test rate
        test_rate = db.query(Rate).filter(Rate.coin_value == 0).first()
        if not test_rate:
            test_rate = Rate(
                coin_value=0,
                minutes=60,
                enabled=True,
            )
            db.add(test_rate)

        db.commit()
        db.refresh(test_client)
        db.refresh(test_rate)
        yield {"client": test_client, "rate": test_rate}
    finally:
        db.close()


def test_admin_create_voucher_json(admin_token):
    from utils.auth import generate_csrf_token
    csrf_token = generate_csrf_token()
    client.cookies.set("admin_token", admin_token)
    client.cookies.set("csrf_token", csrf_token)
    resp = client.post("/api/admin/vouchers", json={
        "minutes": 120,
        "notes": "Test voucher",
    }, headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["minutes"] == 120
    assert data["notes"] == "Test voucher"
    assert data["status"] == "UNUSED"


def test_admin_create_vouchers_bulk_json(admin_token):
    from utils.auth import generate_csrf_token
    csrf_token = generate_csrf_token()
    client.cookies.set("admin_token", admin_token)
    client.cookies.set("csrf_token", csrf_token)
    resp = client.post("/api/admin/vouchers/bulk", json={
        "count": 5,
        "minutes": 60,
        "notes": "Bulk test",
    }, headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["created"] == 5
    assert len(data["vouchers"]) == 5


def test_admin_delete_and_expire_voucher(admin_token):
    from utils.auth import generate_csrf_token
    csrf_token = generate_csrf_token()
    client.cookies.set("admin_token", admin_token)
    client.cookies.set("csrf_token", csrf_token)
    # Create single voucher
    create_resp = client.post("/api/admin/vouchers", json={"minutes": 30}, headers={"X-CSRF-Token": csrf_token})
    voucher_id = create_resp.json()["data"]["id"]

    # Expire voucher
    expire_resp = client.post(f"/api/admin/vouchers/{voucher_id}/expire", headers={"X-CSRF-Token": csrf_token})
    assert expire_resp.status_code == 200

    # Delete voucher
    delete_resp = client.delete(f"/api/admin/vouchers/{voucher_id}", headers={"X-CSRF-Token": csrf_token})
    assert delete_resp.status_code == 200


def test_voucher_redemption_json_body(admin_token, setup_db_data):
    from utils.auth import generate_csrf_token
    csrf_token = generate_csrf_token()
    client.cookies.set("admin_token", admin_token)
    client.cookies.set("csrf_token", csrf_token)
    create_resp = client.post("/api/admin/vouchers", json={"minutes": 60}, headers={"X-CSRF-Token": csrf_token})
    code = create_resp.json()["data"]["code"]

    client.cookies.clear()
    redeem_resp = client.post("/api/v1/voucher/redeem", json={
        "code": code,
        "mac": "00:11:22:33:44:55",
    })
    assert redeem_resp.status_code == 200
    assert redeem_resp.json()["data"]["added_minutes"] == 60

    # Verify Sale record was created
    db = SessionLocal()
    sale = db.query(Sale).filter(Sale.payment_method == PaymentMethod.VOUCHER).order_by(Sale.id.desc()).first()
    assert sale is not None
    assert sale.minutes == 60
    db.close()


def test_voucher_expiration_timezone_safety(admin_token, setup_db_data):
    from utils.auth import generate_csrf_token
    csrf_token = generate_csrf_token()
    client.cookies.set("admin_token", admin_token)
    client.cookies.set("csrf_token", csrf_token)
    # Create voucher with past ISO expiration string
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    create_resp = client.post("/api/admin/vouchers", json={
        "minutes": 60,
        "expires_at": past_iso
    }, headers={"X-CSRF-Token": csrf_token})
    code = create_resp.json()["data"]["code"]

    client.cookies.clear()
    redeem_resp = client.post("/api/v1/voucher/redeem", json={
        "code": code,
        "mac": "00:11:22:33:44:55",
    })
    assert redeem_resp.status_code == 410
    assert "expired" in redeem_resp.json()["detail"].lower()
