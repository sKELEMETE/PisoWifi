import pytest
import bcrypt
from fastapi.testclient import TestClient
from main import app
import config
from utils.rate_limiter import login_limiter
from services.admin_credentials_service import AdminCredentialsService

client = TestClient(app)

ADMIN123_HASH = "$2b$12$zYotO.KE.3lAztq/4t0v1.199gKdAubpYl7arTRvREBkW.6g6FUHC"


@pytest.fixture(autouse=True)
def clean_test_client(mocker):
    login_limiter.records.clear()
    client.cookies.clear()
    orig_username = config.ADMIN_USERNAME
    orig_hash = config.ADMIN_PASSWORD_HASH

    config.ADMIN_USERNAME = "admin"
    config.ADMIN_PASSWORD_HASH = ADMIN123_HASH

    # Prevent credentials tests from modifying the real .env file on disk
    mock_update = mocker.patch.object(AdminCredentialsService, "_update_env_file")
    mock_update.side_effect = lambda target, new_username=None, new_hash=None: (
        setattr(config, 'ADMIN_USERNAME', new_username) if new_username else None,
        setattr(config, 'ADMIN_PASSWORD_HASH', new_hash) if new_hash else None,
        None  # return None (implicit)
    )[-1]

    yield

    config.ADMIN_USERNAME = orig_username
    config.ADMIN_PASSWORD_HASH = orig_hash
    login_limiter.records.clear()
    client.cookies.clear()


def test_service_validation():
    # Valid username
    assert AdminCredentialsService.validate_username("super_admin-1") == "super_admin-1"
    # Invalid username (too short)
    with pytest.raises(ValueError):
        AdminCredentialsService.validate_username("ab")
    # Invalid username (special chars)
    with pytest.raises(ValueError):
        AdminCredentialsService.validate_username("user@name!")

    # Valid password
    assert AdminCredentialsService.validate_password("newsecret123") == "newsecret123"
    # Invalid password (too short)
    with pytest.raises(ValueError):
        AdminCredentialsService.validate_password("12345")


def test_change_credentials_api_unauthorized():
    from utils.auth import generate_csrf_token
    csrf_token = generate_csrf_token()
    client.cookies.set("csrf_token", csrf_token)
    resp = client.post("/api/admin/credentials", json={
        "current_password": "admin123",
        "new_password": "newpassword123"
    }, headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 401


def test_change_password_workflow():
    # Log in first
    login_resp = client.post("/api/admin/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert login_resp.status_code == 200
    assert "admin_token" in login_resp.cookies
    csrf_token = login_resp.json()["data"]["csrf_token"]

    # Change password with wrong current password -> should fail
    resp = client.post("/api/admin/credentials", json={
        "current_password": "wrongcurrentpassword",
        "new_password": "newpassword123"
    }, headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 400
    assert "Current password verification failed" in resp.json()["detail"]

    # Change password with valid current password -> should succeed and invalidate session
    resp = client.post("/api/admin/credentials", json={
        "current_password": "admin123",
        "new_password": "newpassword123"
    }, headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["data"]["password_changed"] is True

    # Active cookie should be cleared
    assert "admin_token" not in resp.cookies or resp.cookies["admin_token"] == ""

    # Login with OLD password -> should fail 401
    fail_login = client.post("/api/admin/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert fail_login.status_code == 401

    # Login with NEW password -> should succeed 200
    success_login = client.post("/api/admin/login", json={
        "username": "admin",
        "password": "newpassword123"
    })
    assert success_login.status_code == 200
    assert success_login.json()["success"] is True
