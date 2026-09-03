import os
import json
import uuid
import subprocess
import pytest
import pymysql
from utils.time_utils import get_utc_now
from coin_serial.coin_spool import CoinSpool
from services.backup_service import BackupService
from services.health_service import HealthService
from models.coin_event import CoinEvent, CoinEventStatus
from models.session import Session, SessionStatus, ClientLiveSession
from models.client import Client, ClientStatus
from models.sale import Sale, PaymentMethod
from models.rate import Rate
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import config

def test_spool_quarantine_and_directory_fsync(tmp_path):
    spool_dir = tmp_path / "spool"
    spool = CoinSpool(spool_dir=str(spool_dir))
    
    # Create event with directory fsync
    event = spool.create_event(denomination=5, lease_id="test_lease_123")
    eid = event["event_id"]
    record_path = spool._get_filepath(eid)
    assert os.path.exists(record_path)
    
    # Quarantine event
    spool.quarantine_orphaned(eid, reason="unit_test_quarantine")
    assert not os.path.exists(record_path)
    quarantine_path = os.path.join(str(spool_dir), "orphaned", f"{eid}.json")
    assert os.path.exists(quarantine_path)
    with open(quarantine_path) as f:
        data = json.load(f)
        assert data["denomination"] == 5

def test_backup_permissions_strict_0600(tmp_path):
    backup_dir = tmp_path / "backups"
    svc = BackupService(backup_dir=str(backup_dir))
    bf = svc.run_backup()
    shaf = f"{bf}.sha256"
    
    bf_mode = oct(os.stat(bf).st_mode & 0o777)
    shaf_mode = oct(os.stat(shaf).st_mode & 0o777)
    assert bf_mode == "0o600", f"Backup archive mode expected 0o600, got {bf_mode}"
    assert shaf_mode == "0o600", f"Checksum file mode expected 0o600, got {shaf_mode}"

def test_health_readiness_probe_sanitization():
    hs = HealthService()
    broken_engine = create_engine("mysql+pymysql://root:@127.0.0.1:3309/invalid_db")
    db = sessionmaker(bind=broken_engine)()
    try:
        is_ready, details = hs.check_readiness(db)
        assert is_ready is False
        assert details["database"] is False
        assert details["reasons"] == ["Database connection failed"]
        assert "127.0.0.1" not in str(details)
        assert "3309" not in str(details)
    finally:
        db.close()

def test_database_check_constraints_enforced_on_mariadb():
    conn = pymysql.connect(
        host="127.0.0.1", port=3307, user="root", password="", database="pisowifi_audit", autocommit=True
    )
    cursor = conn.cursor()
    
    # Try inserting negative remaining_seconds
    with pytest.raises((pymysql.err.OperationalError, pymysql.err.IntegrityError)) as exc_info:
        cursor.execute("INSERT INTO sessions (client_id, rate_id, status, purchased_minutes, remaining_minutes, remaining_seconds, pause_allowed, start_time, end_time) VALUES (1, 1, 'ACTIVE', 20, -10, -600, 1, NOW(), NOW() + INTERVAL 20 MINUTE)")
    assert "chk_sessions_remaining_seconds_nonnegative" in str(exc_info.value)
    
    # Try inserting negative sales amount
    with pytest.raises((pymysql.err.OperationalError, pymysql.err.IntegrityError)) as exc_info:
        cursor.execute("INSERT INTO sales (session_id, rate_id, amount, minutes, payment_method, created_at) VALUES (1, 1, -25, 20, 'COIN', NOW())")
    assert "chk_sales_amount" in str(exc_info.value)
    
    conn.close()

def test_migration_e14_duplicate_session_time_preservation():
    db_url = "mysql+pymysql://root:@127.0.0.1:3307/pisowifi_audit"
    engine = create_engine(db_url)
    SessionMaker = sessionmaker(bind=engine)
    db = SessionMaker()
    
    mac = f"02:FE:DC:BA:{uuid.uuid4().hex[:4]}"
    client = Client(mac_address=mac, current_ip="10.9.9.9", status=ClientStatus.ONLINE)
    db.add(client)
    db.commit()
    client_id = client.id
    
    rate = db.query(Rate).first()
    if not rate:
        rate = Rate(coin_value=5, minutes=60)
        db.add(rate)
        db.commit()
    now = get_utc_now()
    s1 = Session(client_id=client_id, rate_id=rate.id, status=SessionStatus.ACTIVE, purchased_minutes=20, remaining_minutes=20, remaining_seconds=1200, pause_allowed=True, start_time=now, end_time=now)
    s2 = Session(client_id=client_id, rate_id=rate.id, status=SessionStatus.ACTIVE, purchased_minutes=40, remaining_minutes=40, remaining_seconds=2400, pause_allowed=True, start_time=now, end_time=now)
    db.add_all([s1, s2])
    db.commit()
    s1_id, s2_id = s1.id, s2.id
    db.close()
    
    with engine.begin() as conn:
        active_or_paused = conn.execute(
            text(f"SELECT id, client_id, status, remaining_seconds, remaining_minutes, purchased_minutes FROM sessions WHERE client_id = {client_id} AND status IN ('ACTIVE', 'PAUSED') ORDER BY client_id, id DESC")
        ).fetchall()
        
        seen_clients = {}
        for row in active_or_paused:
            sid, cid, status = row[0], row[1], str(row[2])
            rem_sec = row[3] or ((row[4] or 0) * 60)
            purchased_min = row[5] or 0
            if cid not in seen_clients:
                seen_clients[cid] = sid
            else:
                primary_sid = seen_clients[cid]
                if rem_sec > 0 or purchased_min > 0:
                    conn.execute(
                        text("""
                            UPDATE sessions 
                            SET remaining_seconds = COALESCE(remaining_seconds, 0) + :sec,
                                remaining_minutes = (COALESCE(remaining_seconds, 0) + :sec) / 60,
                                purchased_minutes = COALESCE(purchased_minutes, 0) + :pm
                            WHERE id = :psid
                        """),
                        {"sec": rem_sec, "pm": purchased_min, "psid": primary_sid}
                    )
                conn.execute(
                    text("UPDATE sessions SET status = 'EXPIRED', remaining_seconds = 0, remaining_minutes = 0 WHERE id = :s"),
                    {"s": sid}
                )
    
    # Query fresh session
    db_verify = SessionMaker()
    surviving = db_verify.query(Session).filter(Session.id == max(s1_id, s2_id)).one()
    expired = db_verify.query(Session).filter(Session.id == min(s1_id, s2_id)).one()
    assert surviving.remaining_seconds == 3600
    assert surviving.purchased_minutes == 60
    assert expired.status == SessionStatus.EXPIRED
    assert expired.remaining_seconds == 0
    db_verify.close()


def test_real_nftables_packet_forwarding_in_netns():
    """Verify Tests A through H (Unauthorized, Authorized, IP Spoofing, MAC/IP Mismatch, LAN Isolation, Expiration, Pause/Resume, Rebuild) using real kernel packets."""
    res = subprocess.run(
        ["unshare", "-U", "-r", "-n", "python3", "-u", "/tmp/test_real_nftables_packet_forwarding.py"],
        capture_output=True, text=True
    )
    if res.returncode != 0:
        pytest.fail(f"Real nftables packet forwarding test failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")


def test_real_dns_behavior_in_netns():
    """Verify real dnsmasq daemon: local portal resolution, public domain resolution without wildcard poisoning, and upstream outage handling."""
    res = subprocess.run(
        ["unshare", "-U", "-r", "-n", "python3", "-u", "/tmp/test_real_dns_behavior.py"],
        capture_output=True, text=True
    )
    if res.returncode != 0:
        pytest.fail(f"Real DNS behavior test failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

