import time
import jwt
import pytest
import bcrypt
from fastapi.testclient import TestClient
from main import app
import config
from utils.rate_limiter import login_limiter

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_test_client():
    # Ensure rate limiter and client cookie jar are clean before and after every test
    login_limiter.records.clear()
    client.cookies.clear()
    yield
    login_limiter.records.clear()
    client.cookies.clear()

def test_valid_login_plaintext():
    # Temporarily set plaintext mode to verify backward compatibility
    orig_hash = config.ADMIN_PASSWORD_HASH
    orig_plaintext = config.PLAINTEXT_MODE
    config.ADMIN_PASSWORD_HASH = None
    config.PLAINTEXT_MODE = True

    try:
        resp = client.post("/api/admin/login", json={
            "username": config.ADMIN_USERNAME,
            "password": config.ADMIN_PASSWORD
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert "admin_token" in resp.cookies
    finally:
        config.ADMIN_PASSWORD_HASH = orig_hash
        config.PLAINTEXT_MODE = orig_plaintext

def test_valid_login_hash():
    # Test bcrypt hash verification
    orig_hash = config.ADMIN_PASSWORD_HASH
    orig_plaintext = config.PLAINTEXT_MODE
    
    # Generate bcrypt hash of the password
    password = "securepass123"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    config.ADMIN_PASSWORD_HASH = hashed
    config.PLAINTEXT_MODE = False

    try:
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
    finally:
        config.ADMIN_PASSWORD_HASH = orig_hash
        config.PLAINTEXT_MODE = orig_plaintext

def test_invalid_username():
    resp = client.post("/api/admin/login", json={
        "username": "wrongadminusername",
        "password": config.ADMIN_PASSWORD
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
    # Build token with past expiration manually
    past_expire = int(time.time()) - 3600
    payload = {"sub": config.ADMIN_USERNAME, "exp": past_expire}
    expired_jwt = jwt.encode(payload, config.ADMIN_JWT_SECRET, algorithm="HS256")

    client.cookies.set("admin_token", expired_jwt)
    resp = client.get("/api/admin/check")
    assert resp.status_code == 401
    assert "Unauthorized access" in resp.json()["detail"]

def test_logout():
    # Log in first
    resp = client.post("/api/admin/login", json={
        "username": config.ADMIN_USERNAME,
        "password": config.ADMIN_PASSWORD
    })
    assert resp.status_code == 200
    assert "admin_token" in resp.cookies

    # Logout
    resp_logout = client.post("/api/admin/logout")
    assert resp_logout.status_code == 200
    # Cookie should be deleted/cleared
    assert "admin_token" not in resp_logout.cookies or resp_logout.cookies["admin_token"] == ""

def test_lockout():
    # Failed attempts: 5 limit
    for _ in range(5):
        resp = client.post("/api/admin/login", json={
            "username": config.ADMIN_USERNAME,
            "password": "wrongpassword"
        })
        assert resp.status_code == 401

    # 6th attempt should return 429 Too Many Requests
    resp = client.post("/api/admin/login", json={
        "username": config.ADMIN_USERNAME,
        "password": config.ADMIN_PASSWORD
    })
    assert resp.status_code == 429
    assert "Too many failed login attempts" in resp.json()["detail"]
