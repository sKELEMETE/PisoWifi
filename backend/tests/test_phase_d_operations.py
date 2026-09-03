import os
import json
import pytest
from starlette.testclient import TestClient
from main import app
import config
from scheduler.scheduler_service import SchedulerLock, SchedulerService
from services.backup_service import BackupService
from services.health_service import HealthService
from utils.audit_logger import log_audit_event, _sanitize_details, JsonLogFormatter
from utils.auth import create_access_token


def test_scheduler_lock_singleton(tmp_path):
    """Verify SchedulerLock enforces single-instance mutual exclusion."""
    lock_file = str(tmp_path / "test_scheduler.lock")
    lock1 = SchedulerLock(lock_file)
    lock2 = SchedulerLock(lock_file)

    assert lock1.acquire() is True
    # Second concurrent acquire on same lock file must be rejected
    assert lock2.acquire() is False

    lock1.release()
    # After release, acquire succeeds
    assert lock2.acquire() is True
    lock2.release()


def test_scheduler_service_instrumentation():
    """Verify scheduler job execution metrics tracking."""
    service = SchedulerService()
    called = False

    def dummy_job():
        nonlocal called
        called = True

    wrapped = service._instrument_job("test_job", dummy_job)
    wrapped()

    assert called is True
    metrics = service.get_metrics()
    assert "test_job" in metrics["jobs"]
    assert metrics["jobs"]["test_job"]["runs"] == 1
    assert metrics["jobs"]["test_job"]["last_status"] == "SUCCESS"


def test_backup_sha256_and_restore_verification(tmp_path):
    """Verify BackupService produces non-empty backup with SHA256 and validates integrity."""
    backup_dir = str(tmp_path / "backups")
    service = BackupService(backup_dir=backup_dir)

    backup_file = service.run_backup()
    assert os.path.exists(backup_file)
    assert os.path.getsize(backup_file) > 0

    checksum_file = f"{backup_file}.sha256"
    assert os.path.exists(checksum_file)

    # Verify restore integrity on valid backup
    verify_result = service.verify_restore(backup_file)
    assert verify_result["valid"] is True
    assert "sha256" in verify_result
    assert "tables" in verify_result

    # Corrupt backup file and verify restore detects corruption
    with open(backup_file, "ab") as f:
        f.write(b"CORRUPTED_DATA")

    corrupt_result = service.verify_restore(backup_file)
    assert corrupt_result["valid"] is False
    assert "Checksum mismatch" in corrupt_result["error"]


def test_health_live_and_ready_endpoints():
    """Verify liveness and readiness probes respond with HTTP 200 and verified components."""
    client = TestClient(app)

    # Liveness probe
    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "alive"

    # Readiness probe
    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    data = res_ready.json()
    assert data["database"] is True
    assert data["firewall"] is True
    assert data["ready"] is True


def test_health_admin_diagnostics_authorized():
    """Verify /health/admin returns disk, memory, backup, and firewall telemetry for authenticated admin."""
    client = TestClient(app)
    token = create_access_token(config.ADMIN_USERNAME)
    client.cookies.set("admin_token", token)

    res = client.get("/health/admin")
    assert res.status_code == 200
    diag = res.json()
    assert "disk" in diag
    assert "memory" in diag
    assert "backup" in diag
    assert "firewall" in diag
    assert "sessions" in diag


def test_structured_audit_logger_sanitization(tmp_path, monkeypatch):
    """Verify audit logger sanitizes passwords/secrets and writes structured JSON."""
    log_dir = str(tmp_path / "logs")
    monkeypatch.setattr(config, "LOG_DIRECTORY", log_dir)

    # Clear cached singleton logger
    import utils.audit_logger as al
    al._audit_logger = None

    details = {
        "user": "admin",
        "password": "SuperSecretPassword123!",
        "jwt_secret": "my_top_secret_key",
        "action": "login",
    }
    sanitized = _sanitize_details(details)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["jwt_secret"] == "[REDACTED]"
    assert sanitized["user"] == "admin"

    log_audit_event("TEST_EVENT", "admin", "127.0.0.1", "SUCCESS", details)

    audit_file = os.path.join(log_dir, "audit", "audit.log")
    assert os.path.exists(audit_file)

    with open(audit_file, "r") as f:
        line = f.readline()
        record = json.loads(line)

    assert record["event_type"] == "TEST_EVENT"
    assert record["actor"] == "admin"
    assert record["details"]["password"] == "[REDACTED]"
    assert "SuperSecretPassword123!" not in line
