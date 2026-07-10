import logging
from database import SessionLocal
from models.session import Session as SessionModel
from models.client import Client
from services.firewall_service import FirewallService

logger = logging.getLogger(__name__)

def expire_sessions():
    db = SessionLocal()
    try:
        firewall = FirewallService()
        active_sessions = db.query(SessionModel).filter(SessionModel.status == "ACTIVE").all()

        for session in active_sessions:
            if session.remaining_minutes > 0:
                session.remaining_minutes -= 1
            else:
                session.status = "EXPIRED"
                client = db.query(Client).filter(Client.id == session.client_id).first()
                if client and client.current_ip:
                    firewall.remove(client.current_ip)

        db.commit()
    except Exception as e:
        logger.error("Session expiration failed: %s", e)
    finally:
        db.close()

def sync_firewall():
    logger.info("Running firewall synchronization.")

def check_health():
    logger.info("Running health monitoring.")

def cleanup():
    logger.info("Running cleanup.")

def backup():
    logger.info("Running backup.")
