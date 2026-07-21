import time
import jwt
import pytest
import bcrypt
from fastapi.testclient import TestClient
from main import app
import config
from utils.rate_limiter import login_limiter

client = TestClient(app)

# Standard bcrypt hash for "admin123"
ADMIN123_HASH = "$2b$12$zYotO.KE.3lAztq/4t0v1.199gKdAubpYl7arTRvREBkW.6g6FUHC"

@pytest.fixture(autouse=True)
def clean_test_client():
    login_limiter.records.clear()
    client.cookies.clear()
    orig_hash = config.ADMIN_PASSWORD_HASH
    
    config.ADMIN_PASSWORD_HASH = ADMIN123_HASH
    
    yield
    
    config.ADMIN_PASSWORD_HASH = orig_hash
    login_limiter.records.clear()
    client.cookies.clear()

def test_valid_login_hash():
    password = "securepass123"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    config.ADMIN_PASSWORD_HASH = hashed

    # Invalid password check
    resp = client.post("/api/admin/login", json={
        "username": config.ADMIN_USERNAME,
        "password": "wrongpassword"
    })
    assert resp.status_code == 401

    # Valid password check
    resp = client.post("/api/admin/login", json={
        "username": config.ADMIN_USERNAME,
        "password": password
    })
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert "admin_token" in resp.cookies

def test_invalid_username():
    resp = client.post("/api/admin/login", json={
        "username": "wrongadminusername",
        "password": "admin123"
    })
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.json()["detail"]

def test_invalid_password():
    resp = client.post("/api/admin/login", json={
        "username": config.ADMIN_USERNAME,
        "password": "incorrectpassword123"
    })
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.json()["detail"]

def test_missing_cookie():
    resp = client.get("/api/admin/check")
    assert resp.status_code == 401
    assert "Unauthorized access" in resp.json()["detail"]

def test_malformed_token():
    client.cookies.set("admin_token", "invalid.jwt.token.string.here")
    resp = client.get("/api/admin/check")
    assert resp.status_code == 401
    assert "Unauthorized access" in resp.json()["detail"]

def test_expired_token():
    past_expire = int(time.time()) - 3600
    payload = {"sub": config.ADMIN_USERNAME, "exp": past_expire, "iat": past_expire - 3600}
    expired_jwt = jwt.encode(payload, config.ADMIN_JWT_SECRET, algorithm="HS256")

    client.cookies.set("admin_token", expired_jwt)
    resp = client.get("/api/admin/check")
    assert resp.status_code == 401
    assert "Unauthorized access" in resp.json()["detail"]

def test_logout():
    resp = client.post("/api/admin/login", json={
        "username": config.ADMIN_USERNAME,
        "password": "admin123"
    })
    assert resp.status_code == 200
    assert "admin_token" in resp.cookies
    csrf_token = resp.json()["data"]["csrf_token"]

    resp_logout = client.post("/api/admin/logout", headers={"X-CSRF-Token": csrf_token})
    assert resp_logout.status_code == 200
    assert "admin_token" not in resp_logout.cookies or resp_logout.cookies["admin_token"] == ""

def test_lockout():
    for _ in range(5):
        resp = client.post("/api/admin/login", json={
            "username": config.ADMIN_USERNAME,
            "password": "wrongpassword"
        })
        assert resp.status_code == 401

    resp = client.post("/api/admin/login", json={
        "username": config.ADMIN_USERNAME,
        "password": "admin123"
    })
    assert resp.status_code == 429
    assert "Too many failed login attempts" in resp.json()["detail"]
