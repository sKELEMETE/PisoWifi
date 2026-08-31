import logging
from datetime import datetime, timedelta
from utils.time_utils import get_utc_now
from sqlalchemy import select, func
from database import SessionLocal
from models.session import Session as SessionModel, SessionStatus
from models.client import Client
from services.firewall_service import FirewallService
import config

logger = logging.getLogger(__name__)

_last_system_time = None
_last_monotonic_time = None

def check_expired_reservations(db):
    """
    Find expired coin reservations and finalize/release them.
    """
    from models.coin_reservation import CoinReservation, PendingCoin
    from repositories.rate_repository import RateRepository
    from repositories.client_repository import ClientRepository
    from repositories.sales_repository import SalesRepository
    from repositories.session_repository import SessionRepository
    from services.session_service import SessionService
    from services.coin_service import CoinService

    now = get_utc_now()
    expired = db.query(CoinReservation).filter(CoinReservation.expires_at <= now).all()
    if expired:
        from services.hardware_service import hardware_service
        try:
            hardware_service.set_accepting(False)
        except Exception as exc:
            logger.error("Failed to force coin relay OFF for expired lease: %s", exc)
    client_repo = ClientRepository(db)
    for res in expired:
        mac = res.mac
        masked_mac = f"**:**:**:**:{mac[-5:]}"
        logger.info("Scheduler: coin lease timed out for %s. Finalizing...", masked_mac)
        try:
            pending_records = db.query(PendingCoin).filter(PendingCoin.mac == mac).all()
            coins = [r.amount for r in pending_records]
            if coins:
                coin_service = CoinService(
                    rate_repository=RateRepository(db),
                    client_repository=client_repo,
                    session_service=SessionService(SessionRepository(db)),
                    sale_repository=SalesRepository(db),
                )
                coin_service.process_coins_bulk(mac, coins, authorize=True, commit=False)

            db.query(CoinReservation).filter(CoinReservation.mac == mac).delete()
            db.query(PendingCoin).filter(PendingCoin.mac == mac).delete()
            db.commit()

            if coins:
                client = client_repo.get_by_mac(mac)
                if client and client.current_ip:
                    try:
                        FirewallService().authorize(client.current_ip)
                    except Exception as auth_exc:
                        logger.error("Scheduler: failed to authorize %s after coin processing: %s", mac, auth_exc)

            logger.info("Scheduler: slot successfully released for %s.", masked_mac)
        except Exception as exc:
            db.rollback()
            logger.error("Scheduler: failed to finalize expired reservation for %s: %s", masked_mac, exc)


def check_expired_reservations_job():
    db = SessionLocal()
    try:
        check_expired_reservations(db)
    except Exception as exc:
        logger.error("Coin lease expiration check failed: %s", exc)
    finally:
        db.close()


def expire_sessions():
    global _last_system_time, _last_monotonic_time
    import time

    db = SessionLocal()
    try:
        firewall = FirewallService()
        now = get_utc_now()
        current_mono = time.monotonic()

        # Compensate for system clock jumps (e.g. NTP sync) to protect session remaining time
        if _last_system_time is not None and _last_monotonic_time is not None:
            system_diff = (now - _last_system_time).total_seconds()
            monotonic_diff = current_mono - _last_monotonic_time
            if abs(system_diff - monotonic_diff) > 5.0:
                jump_seconds = system_diff - monotonic_diff
                logger.warning("Clock jump of %s seconds detected. Adjusting session end_times...", jump_seconds)
                try:
                    from sqlalchemy import update
                    db.execute(
                        update(SessionModel)
                        .where(SessionModel.status == SessionStatus.ACTIVE)
                        .values(end_time=SessionModel.end_time + timedelta(seconds=jump_seconds))
                    )
                    db.commit()
                except Exception as exc:
                    logger.error("Failed to compensate active session end times for clock jump: %s", exc)

        _last_system_time = now
        _last_monotonic_time = current_mono

        # Expire ACTIVE sessions whose end_time has passed.
        # Single JOIN query to avoid N+1 client lookups.
        expired_active = db.execute(
            select(SessionModel, Client.current_ip)
            .join(Client, Client.id == SessionModel.client_id)
            .where(SessionModel.status == SessionStatus.ACTIVE)
            .where(SessionModel.end_time <= now)
        ).all()

        for session, client_ip in expired_active:
            session.status = SessionStatus.EXPIRED
            session.remaining_minutes = 0
            session.remaining_seconds = 0
            if client_ip:
                firewall.remove(client_ip)

        # Expire stale PAUSED sessions:
        #   - sessions with zero remaining time (remaining_seconds <= 0 and remaining_minutes <= 0)
        #   - sessions paused longer than PAUSE_EXPIRATION_DAYS
        stale_cutoff = now - timedelta(days=config.PAUSE_EXPIRATION_DAYS)
        stale_paused = db.execute(
            select(SessionModel, Client.current_ip)
            .join(Client, Client.id == SessionModel.client_id)
            .where(SessionModel.status == SessionStatus.PAUSED)
            .where(
                ((SessionModel.remaining_seconds.is_(None) | (SessionModel.remaining_seconds <= 0)) & (SessionModel.remaining_minutes <= 0)) |
                (SessionModel.paused_at <= stale_cutoff)
            )
        ).all()

        for session, client_ip in stale_paused:
            session.status = SessionStatus.EXPIRED
            session.remaining_minutes = 0
            session.remaining_seconds = 0
            if client_ip:
                firewall.remove(client_ip)

        db.commit()

    except Exception as e:
        logger.error("Session expiration lookup failed: %s", e)
    finally:
        db.close()

def sync_firewall():
    import json
    import subprocess
    from database import SessionLocal
    from models.session import Session as SessionModel, SessionStatus
    from models.client import Client
    from services.firewall_service import FirewallService

    db = SessionLocal()
    try:
        firewall = FirewallService()
        # 1. Get active IPs from database
        active_ips = db.execute(
            select(Client.current_ip)
            .join(SessionModel, SessionModel.client_id == Client.id)
            .where(SessionModel.status == SessionStatus.ACTIVE)
        ).scalars().all()
        active_ips = {ip for ip in active_ips if ip}

        # 2. Get actual IPs from nftables sets
        nft_ips = set()
        for family, table, set_name in [("inet", config.NFT_TABLE_NAME, config.NFT_SET_NAME), ("ip", "nat", config.NFT_SET_NAME)]:
            cmd = [config.PATH_NFT, "-j", "list", "set", family, table, set_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    for obj in data.get("nftables", []):
                        if "set" in obj and "elem" in obj["set"]:
                            nft_ips.update(obj["set"]["elem"])
                except Exception:
                    pass

        # 3. Remove orphans (IP in nftables but not active in DB)
        orphans = nft_ips - active_ips
        for ip in orphans:
            logger.info("Firewall Auditor: removing orphan IP %s", ip)
            try:
                firewall.remove(ip)
            except Exception as exc:
                logger.error("Firewall Auditor: failed to remove orphan %s: %s", ip, exc)

        # 4. Restore missing (IP active in DB but missing from nftables)
        missing = active_ips - nft_ips
        for ip in missing:
            logger.info("Firewall Auditor: authorizing missing IP %s", ip)
            try:
                firewall.authorize(ip)
            except Exception as exc:
                logger.error("Firewall Auditor: failed to restore missing %s: %s", ip, exc)

    except Exception as e:
        logger.error("Firewall Auditor sync failed: %s", e)
    finally:
        db.close()

def backup():
    """Scheduled daily database backup job."""
    from services.backup_service import BackupService
    try:
        logger.info("Scheduled job: Starting database backup...")
        service = BackupService()
        backup_path = service.run_backup()
        logger.info("Scheduled job: Database backup completed successfully -> %s", backup_path)
    except Exception as exc:
        logger.error("Scheduled job: Database backup failed: %s", exc)
