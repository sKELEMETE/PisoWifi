import logging
from datetime import datetime, timedelta
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
        
        # Expire ACTIVE sessions whose end_time has passed
        expired_active = db.query(SessionModel).filter(
            SessionModel.status == "ACTIVE",
            SessionModel.end_time <= now
        ).all()

        for session in expired_active:
            session.status = "EXPIRED"
            session.remaining_minutes = 0
            client = db.query(Client).filter(Client.id == session.client_id).first()
            if client and client.current_ip:
                firewall.remove(client.current_ip)

        # Expire stale PAUSED sessions:
        #   - sessions with zero remaining seconds (remaining_minutes column holds seconds while paused)
        #   - sessions paused longer than PAUSE_EXPIRATION_DAYS
        stale_cutoff = now - timedelta(days=config.PAUSE_EXPIRATION_DAYS)
        stale_paused = db.query(SessionModel).filter(
            SessionModel.status == "PAUSED",
            (
                (SessionModel.remaining_minutes <= 0) |
                (SessionModel.paused_at <= stale_cutoff)
            )
        ).all()

        for session in stale_paused:
            session.status = "EXPIRED"
            session.remaining_minutes = 0
            client = db.query(Client).filter(Client.id == session.client_id).first()
            if client and client.current_ip:
                firewall.remove(client.current_ip)

        db.commit()
    except Exception as e:
        logger.error("Session expiration lookup failed: %s", e)
    finally:
        db.close()

def sync_firewall(): pass
def check_health(): pass
def cleanup(): pass
def backup(): pass