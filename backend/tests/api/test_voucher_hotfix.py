import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import app
from database import SessionLocal
from models.voucher import Voucher, VoucherStatus
from models.client import Client
from utils.auth import verify_password
from services.firewall_service import FirewallService
import config

client = TestClient(app)

ADMIN123_HASH = "$2b$12$zYotO.KE.3lAztq/4t0v1.199gKdAubpYl7arTRvREBkW.6g6FUHC"

@pytest.fixture(autouse=True)
def mock_firewall(mocker):
    mocker.patch.object(FirewallService, "authorize", return_value=None)
    mocker.patch.object(FirewallService, "remove", return_value=None)
    orig_username = config.ADMIN_USERNAME
    orig_hash = config.ADMIN_PASSWORD_HASH
    config.ADMIN_USERNAME = "admin"
    config.ADMIN_PASSWORD_HASH = ADMIN123_HASH
    yield
    config.ADMIN_USERNAME = orig_username
    config.ADMIN_PASSWORD_HASH = orig_hash


def test_admin_login_success():
    res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "admin_token" in res.cookies

def test_admin_login_invalid_password():
    res = client.post("/api/admin/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401
    assert res.json()["success"] is False

def test_verify_password_malformed_hash_logging(caplog):
    # Test that a malformed hash logs error cleanly without crashing
    original_hash = config.ADMIN_PASSWORD_HASH
    config.ADMIN_PASSWORD_HASH = "malformed_hash_string"
    try:
        res = verify_password("admin123")
        assert res is False
        assert "Bcrypt configuration/hash validation failed" in caplog.text
    finally:
        config.ADMIN_PASSWORD_HASH = original_hash

def test_voucher_management_lifecycle():
    # 1. Admin login
    login_res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200
    csrf_token = login_res.json()["data"]["csrf_token"]
    cookies = login_res.cookies

    # 2. Create single voucher
    create_res = client.post("/api/admin/vouchers", json={"minutes": 60, "notes": "Hotfix test"}, cookies=cookies, headers={"X-CSRF-Token": csrf_token})
    assert create_res.status_code == 201
    voucher_data = create_res.json()["data"]
    v_id = voucher_data["id"]
    v_code = voucher_data["code"]
    assert voucher_data["minutes"] == 60

    # 3. Create bulk vouchers
    bulk_res = client.post("/api/admin/vouchers/bulk", json={"count": 5, "minutes": 30}, cookies=cookies, headers={"X-CSRF-Token": csrf_token})
    assert bulk_res.status_code == 201
    assert bulk_res.json()["data"]["created"] == 5

    # 4. List vouchers
    list_res = client.get("/api/admin/vouchers?limit=10", cookies=cookies)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]["vouchers"]) > 0

    # 5. Voucher stats
    stats_res = client.get("/api/admin/vouchers/stats", cookies=cookies)
    assert stats_res.status_code == 200
    assert stats_res.json()["data"]["total"] > 0

    # 6. Export CSV
    export_csv = client.get("/api/admin/vouchers/export?format=csv", cookies=cookies)
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers["content-type"]

    # 7. Expire voucher
    expire_res = client.post(f"/api/admin/vouchers/{v_id}/expire", cookies=cookies, headers={"X-CSRF-Token": csrf_token})
    assert expire_res.status_code == 200
    assert expire_res.json()["success"] is True

    # 8. Delete voucher
    delete_res = client.delete(f"/api/admin/vouchers/{v_id}", cookies=cookies, headers={"X-CSRF-Token": csrf_token})
    assert delete_res.status_code == 200
    assert delete_res.json()["success"] is True

def test_voucher_redemption_for_new_client():
    # 1. Create a voucher via admin
    login_res = client.post("/api/admin/login", json={"username": "admin", "password": "admin123"})
    csrf_token = login_res.json()["data"]["csrf_token"]
    cookies = login_res.cookies

    create_res = client.post("/api/admin/vouchers", json={"minutes": 120}, cookies=cookies, headers={"X-CSRF-Token": csrf_token})
    v_code = create_res.json()["data"]["code"]

    # 2. Redeem using a completely NEW client MAC address (not in DB)
    new_mac = "12:34:56:78:90:AB"
    redeem_res = client.post("/api/v1/voucher/redeem", json={"code": v_code, "mac": new_mac})
    assert redeem_res.status_code == 200
    assert redeem_res.json()["success"] is True
    assert redeem_res.json()["data"]["added_minutes"] == 120

    # 3. Verify client was created automatically
    db = SessionLocal()
    c = db.query(Client).filter(Client.mac_address == new_mac).first()
    assert c is not None
    db.close()

    # 4. Attempt double redemption of same voucher -> 409 Conflict
    redeem_again = client.post("/api/v1/voucher/redeem", json={"code": v_code, "mac": new_mac})
    assert redeem_again.status_code == 409
    assert redeem_again.json()["detail"] == "Voucher already used"
