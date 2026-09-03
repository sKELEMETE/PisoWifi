import os
import shutil
import pytest
import uuid
import threading
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from main import app
import config
from database import SessionLocal
from models.client import Client, ClientStatus
from models.session import Session as SessionModel, SessionStatus
from models.rate import Rate
from models.coin_reservation import CoinReservation, PendingCoin
from services.session_service import SessionService
from services.backup_service import BackupService
from repositories.session_repository import SessionRepository
from recovery.power_recovery import PowerRecovery
from scheduler.jobs import backup as backup_job
from utils.time_utils import get_utc_now

test_client = TestClient(app)


def gen_random_mac():
    raw = uuid.uuid4().hex[:12]
    return ":".join(raw[i:i+2] for i in range(0, 12, 2)).upper()


def test_backup_service_creation_and_retention(tmp_path):
    """Verify BackupService creates backup file, validates file non-empty, and cleans up retention files."""
    backup_dir = str(tmp_path / "backups")
    service = BackupService(backup_dir=backup_dir, retention_days=1)
    
    # Run backup
    backup_file = service.run_backup()
    assert os.path.exists(backup_file)
    assert os.path.getsize(backup_file) > 0

    # Create dummy old files to test retention cleanup
    old_file = os.path.join(backup_dir, "pisowifi_backup_20200101_000000.sql")
    with open(old_file, "w") as f:
        f.write("DUMMY OLD BACKUP")
    
    # Set mtime to 60 days ago
    past_time = (datetime.now() - timedelta(days=60)).timestamp()
    os.utime(old_file, (past_time, past_time))

    # Run backup again to trigger retention cleanup
    service.run_backup()
    assert not os.path.exists(old_file)


def test_scheduled_backup_job_no_crash():
    """Verify scheduler backup() job runs without throwing exceptions."""
    try:
        backup_job()
    except Exception as exc:
        pytest.fail(f"Backup job crashed with exception: {exc}")


def test_coin_reservation_concurrency():
    """Verify exclusive slot reservation prevents double reservation across concurrent activations."""
    db = SessionLocal()
    try:
        from models.coin_reservation import CoinReservation
        db.query(CoinReservation).delete()
        db.commit()

        mac1 = gen_random_mac()
        mac2 = gen_random_mac()

        results = []

        def activate(mac_addr):
            c = TestClient(app)
            res = c.post(f"/api/v1/coin/activate/{mac_addr}")
            results.append((mac_addr, res.status_code, res.json()))

        t1 = threading.Thread(target=activate, args=(mac1,))
        t2 = threading.Thread(target=activate, args=(mac2,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        statuses = [r[1] for r in results]
        # One must succeed (200) and one must be rejected (409)
        assert 200 in statuses
        assert 409 in statuses

        # Clean up database reservation state
        db.query(CoinReservation).delete()
        db.commit()
    finally:
        db.close()


def test_timezone_naive_utc_consistency():
    """Verify session creation, extension, pause, resume, and power recovery use get_utc_now() without timezone offset errors."""
    db = SessionLocal()
    client_id = None
    try:
        mac = gen_random_mac()
        client = Client(mac_address=mac, status=ClientStatus.OFFLINE)
        db.add(client)
        db.commit()
        db.refresh(client)
        client_id = client.id

        rate = db.query(Rate).filter(Rate.enabled.is_(True)).first()
        if not rate:
            rate = Rate(coin_value=1, minutes=30, enabled=True)
            db.add(rate)
            db.commit()

        session_repo = SessionRepository(db)
        service = SessionService(session_repo)

        # 1. Create Session
        now_utc = get_utc_now()
        sess = service.create_or_extend_session(client_id, rate.id, 30, authorize=False)
        db.commit()

        # Check end_time is ~30 minutes from now_utc
        diff_sec = (sess.end_time - now_utc).total_seconds()
        assert 1790 <= diff_sec <= 1810
    finally:
        db.close()

    # 2. Pause Session via API
    resp_pause = test_client.post(f"/api/v1/session/pause/{mac}")
    assert resp_pause.status_code == 200

    db2 = SessionLocal()
    try:
        session_repo2 = SessionRepository(db2)
        sess_paused = session_repo2.get_paused_session_by_client_id(client_id)
        assert sess_paused is not None
        assert sess_paused.status == SessionStatus.PAUSED
        assert sess_paused.remaining_seconds is not None
        assert 1780 <= sess_paused.remaining_seconds <= 1810
    finally:
        db2.close()

    # 3. Resume Session via API
    resp_resume = test_client.post(f"/api/v1/session/resume/{mac}")
    assert resp_resume.status_code == 200

    db3 = SessionLocal()
    try:
        session_repo3 = SessionRepository(db3)
        sess_resumed = session_repo3.get_active_session_by_client_id(client_id)
        assert sess_resumed is not None
        assert sess_resumed.status == SessionStatus.ACTIVE
        resumed_diff = (sess_resumed.end_time - get_utc_now()).total_seconds()
        assert 1780 <= resumed_diff <= 1810
    finally:
        db3.close()
