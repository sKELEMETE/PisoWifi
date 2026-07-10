from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from repositories.session_repository import SessionRepository
from repositories.client_repository import ClientRepository
from services.firewall_service import FirewallService
from schemas.validation import MacRequest
from utils.api_response import success, error

router = APIRouter(prefix="/api/v1/session", tags=["Session"])

@router.get("/{mac}")
def get_session(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    client_repo = ClientRepository(db)
    session_repo = SessionRepository(db)

    client = client_repo.get_by_mac(validated.mac)
    if not client:
        return error("Client not found", ["MAC invalid"])

    session = session_repo.get_active_session_by_client_id(client.id)
    if not session:
        return error("No active session", ["Session missing"])

    return success({
        "session_id": session.id,
        "status": session.status,
        "remaining_seconds": session.remaining_minutes * 60,
    })

@router.post("/pause/{mac}")
def pause_session(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    client_repo = ClientRepository(db)
    session_repo = SessionRepository(db)
    firewall = FirewallService()

    client = client_repo.get_by_mac(validated.mac)
    if not client:
        return error("Client not found")

    session = session_repo.get_active_session_by_client_id(client.id)
    if not session:
        return error("No active session")

    session.status = "PAUSED"
    db.commit()

    if client.current_ip:
        firewall.remove(client.current_ip)

    return success({
        "session_id": session.id,
        "status": "PAUSED",
    })

@router.post("/resume/{mac}")
def resume_session(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    client_repo = ClientRepository(db)
    session_repo = SessionRepository(db)
    firewall = FirewallService()

    client = client_repo.get_by_mac(validated.mac)
    if not client:
        return error("Client not found")

    session = session_repo.get_paused_session_by_client_id(client.id)
    if not session:
        return error("No paused session")

    session.status = "ACTIVE"
    db.commit()

    if client.current_ip:
        firewall.authorize(client.current_ip)

    return success({
        "session_id": session.id,
        "status": "ACTIVE",
    })
