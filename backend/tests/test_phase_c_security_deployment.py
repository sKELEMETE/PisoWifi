import os
import stat
import subprocess
import pytest
from starlette.testclient import TestClient
import config
from main import app
from utils.auth import create_access_token, verify_access_token


def test_admin_jwt_secret_length_and_rfc7518_compliance():
    """Verify that ADMIN_JWT_SECRET is at least 32 bytes (256 bits) per RFC 7518."""
    assert len(config.ADMIN_JWT_SECRET.encode("utf-8")) >= 32
    token = create_access_token("admin")
    decoded = verify_access_token(token)
    assert decoded == "admin"


def test_env_example_and_git_untracking():
    """Verify .env.example exists with documentation and .env.bak is untracked by git."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root_example = os.path.join(repo_root, ".env.example")
    backend_example = os.path.join(repo_root, "backend/.env.example")

    assert os.path.exists(root_example), ".env.example missing at repo root"
    assert os.path.exists(backend_example), "backend/.env.example missing"

    with open(root_example, "r") as f:
        content = f.read()
    assert "ADMIN_JWT_SECRET" in content
    assert "DATABASE_PASSWORD" in content
    assert "PISOWIFI_DATABASE_TYPE" in content

    # Check git tracking: backend/.env.bak must NOT be tracked
    res = subprocess.run(
        ["git", "ls-files", "backend/.env.bak"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    assert res.stdout.strip() == "", "backend/.env.bak should NOT be tracked in git index!"


def test_env_file_permissions():
    """Verify .env files have restricted permissions (0600) to prevent unauthorized read."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for env_path in (os.path.join(repo_root, ".env"), os.path.join(repo_root, "backend/.env")):
        if os.path.exists(env_path):
            mode = stat.S_IMODE(os.stat(env_path).st_mode)
            assert mode == 0o600, f"{env_path} does not have 0600 permissions (actual: {oct(mode)})"


def test_mariadb_setup_script_and_systemd_hardening():
    """Verify setup_mariadb.sh exists and systemd units have required hardening directives."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    setup_script = os.path.join(repo_root, "scripts/setup_mariadb.sh")

    assert os.path.exists(setup_script)
    assert os.access(setup_script, os.X_OK)

    with open(setup_script, "r") as f:
        script_content = f.read()
    assert "innodb_flush_log_at_trx_commit = 2" in script_content
    assert "innodb_buffer_pool_size = 128M" in script_content

    systemd_tmpl = os.path.join(repo_root, "config/systemd/pisowifi-backend.service.template")
    with open(systemd_tmpl, "r") as f:
        sys_content = f.read()

    assert "Requires=mariadb.service" in sys_content
    assert "RestartSec=3s" in sys_content
    assert "LimitNOFILE=65535" in sys_content
    assert "PrivateTmp=true" in sys_content


def test_management_plane_separation_in_nginx():
    """Verify captive portal config rejects /api/admin and dedicates port 8443 with SSL."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    nginx_tmpl = os.path.join(repo_root, "config/nginx/pisowifi.conf.template")

    with open(nginx_tmpl, "r") as f:
        content = f.read()

    assert "location ^~ /api/admin/" in content
    assert "return 403" in content
    assert "listen 8443 ssl" in content
    assert "ssl_certificate" in content


def test_admin_login_https_enforcement_in_production(monkeypatch):
    """Verify admin login rejects non-HTTPS requests when originating from non-loopback clients in production."""
    client = TestClient(app)

    monkeypatch.setattr(config, "ENVIRONMENT", "production")

    # Request from external LAN IP over HTTP
    headers = {
        "x-forwarded-proto": "http",
        "x-forwarded-for": "192.168.4.55",
    }
    res = client.post(
        "/api/admin/login",
        json={"username": config.ADMIN_USERNAME, "password": "password"},
        headers=headers
    )
    # Must be 403 Forbidden due to missing HTTPS
    assert res.status_code == 403
    assert "HTTPS is required" in res.json()["detail"]

    # Request with HTTPS proto
    headers_https = {
        "x-forwarded-proto": "https",
        "x-forwarded-for": "192.168.4.55",
    }
    res_https = client.post(
        "/api/admin/login",
        json={"username": config.ADMIN_USERNAME, "password": "wrongpassword"},
        headers=headers_https
    )
    # Passes HTTPS barrier to authentication logic (401 invalid password)
    assert res_https.status_code == 401
