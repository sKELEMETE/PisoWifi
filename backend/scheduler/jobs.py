import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func
from database import SessionLocal
from models.session import Session as SessionModel
from models.client import Client
from services.firewall_service import FirewallService
import config

logger = logging.getLogger(__name__)

def expire_sessions():
    db = SessionLocal()
    try:
        firewall = FirewallService()
        now = datetime.now()

        # Expire ACTIVE sessions whose end_time has passed.
        # Single JOIN query to avoid N+1 client lookups.
        expired_active = db.execute(
            select(SessionModel, Client.current_ip)
            .join(Client, Client.id == SessionModel.client_id)
            .where(SessionModel.status == "ACTIVE")
            .where(SessionModel.end_time <= now)
        ).all()

        for session, client_ip in expired_active:
            session.status = "EXPIRED"
            session.remaining_minutes = 0
            if client_ip:
                firewall.remove(client_ip)

        # Expire stale PAUSED sessions:
        #   - sessions with zero remaining seconds (remaining_minutes column holds seconds while paused)
        #   - sessions paused longer than PAUSE_EXPIRATION_DAYS
        stale_cutoff = now - timedelta(days=config.PAUSE_EXPIRATION_DAYS)
        stale_paused = db.execute(
            select(SessionModel, Client.current_ip)
            .join(Client, Client.id == SessionModel.client_id)
            .where(SessionModel.status == "PAUSED")
            .where(
                (SessionModel.remaining_minutes <= 0) |
                (SessionModel.paused_at <= stale_cutoff)
            )
        ).all()

        for session, client_ip in stale_paused:
            session.status = "EXPIRED"
            session.remaining_minutes = 0
            if client_ip:
                firewall.remove(client_ip)

        db.commit()
    except Exception as e:
        logger.error("Session expiration lookup failed: %s", e)
    finally:
        db.close()

def backup(): pass