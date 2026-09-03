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
    Find expired coin reservations and finalize/release them via CoinSettlementService.
    """
    from models.coin_reservation import CoinReservation
    from services.coin_settlement_service import CoinSettlementService

    now = get_utc_now()
    expired = db.query(CoinReservation).filter(CoinReservation.expires_at <= now).all()
    if expired:
        from services.hardware_service import hardware_service
        try:
            hardware_service.set_accepting(False)
        except Exception as exc:
            logger.error("Failed to force coin relay OFF for expired lease: %s", exc)

    settlement = CoinSettlementService(db)
    for res in expired:
        mac = res.mac
        lease_id = res.lease_id
        masked_mac = f"**:**:**:**:{mac[-5:]}" if len(mac) >= 5 else mac
        logger.info("Scheduler: coin lease timed out for %s. Finalizing via CoinSettlementService...", masked_mac)
        try:
            settlement.finalize_lease(lease_id=lease_id, mac=mac, authorize=True)
        except Exception as exc:
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
    from models.session import ClientLiveSession

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

        # Checkpoint running active sessions to protect remaining time across unexpected power loss
        active_sessions = db.query(SessionModel).filter(SessionModel.status == SessionStatus.ACTIVE).all()
        for s in active_sessions:
            cur_rem = max(0, int((s.end_time - now).total_seconds())) if s.end_time else 0
            s.remaining_seconds = cur_rem
            s.remaining_minutes = cur_rem // 60
            s.last_accounted_at = now

        # Expire ACTIVE sessions whose end_time has passed.
        # Single JOIN query to avoid N+1 client lookups.
        expired_active = db.execute(
            select(SessionModel, Client.current_ip)
            .join(Client, Client.id == SessionModel.client_id)
            .where(SessionModel.status == SessionStatus.ACTIVE)
            .where(SessionModel.end_time <= now)
        ).all()

        expired_ids = []
        for session, client_ip in expired_active:
            session.status = SessionStatus.EXPIRED
            session.remaining_minutes = 0
            session.remaining_seconds = 0
            expired_ids.append(session.id)
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
            expired_ids.append(session.id)
            if client_ip:
                firewall.remove(client_ip)

        if expired_ids:
            from models.network_authorization import NetworkAuthorization, NetworkAuthState
            db.query(ClientLiveSession).filter(ClientLiveSession.session_id.in_(expired_ids)).delete(synchronize_session=False)
            db.query(NetworkAuthorization).filter(NetworkAuthorization.session_id.in_(expired_ids)).update(
                {"desired_state": NetworkAuthState.BLOCKED.value},
                synchronize_session=False
            )

        db.commit()

    except Exception as e:
        logger.error("Session expiration lookup failed: %s", e)
    finally:
        db.close()


def sync_firewall():
    """Continuously reconciles database network authorization state with running firewall rules."""
    from database import SessionLocal
    from services.firewall_reconciler import FirewallReconciler

    db = SessionLocal()
    try:
        reconciler = FirewallReconciler()
        metrics = reconciler.reconcile_once(db)
        if metrics["out_of_sync_count"] > 0:
            logger.info("Firewall Reconciler completed: %s", metrics)
    except Exception as exc:
        logger.error("Firewall Reconciler job failed: %s", exc)
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
