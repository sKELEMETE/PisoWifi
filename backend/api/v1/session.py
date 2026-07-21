from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta
from database import get_db
from models.client import Client
from models.session import Session as SessionModel, SessionStatus
from repositories.session_repository import SessionRepository
from repositories.client_repository import ClientRepository
from services.firewall_service import FirewallService
from schemas.validation import MacRequest
from utils.api_response import success, error
from utils.time_utils import get_utc_now

router = APIRouter(prefix="/api/v1/session", tags=["Session"])

@router.get("/{mac}")
def get_session(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)

    # Consolidate client and session lookups into a single LEFT OUTER JOIN query
    stmt = (
        select(Client, SessionModel)
        .outerjoin(
            SessionModel,
            (SessionModel.client_id == Client.id) & SessionModel.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED])
        )
        .where(Client.mac_address == validated.mac)
        .order_by(SessionModel.id.desc())
    )
    row = db.execute(stmt).first()

    if not row:
        return error("Client not found", ["MAC invalid"])

    client, session = row
    if not session:
        return error("No active session", ["Session missing"])

    now = get_utc_now()
    if session.status == SessionStatus.PAUSED:
        if session.remaining_seconds is not None and session.remaining_seconds > 0:
            remaining_seconds = session.remaining_seconds
        else:
            remaining_seconds = (session.remaining_minutes or 0) * 60
    else:
        remaining_seconds = max(0, int((session.end_time - now).total_seconds()))

    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60
    seconds = remaining_seconds % 60
    remaining_time = f"{hours:02}:{minutes:02}:{seconds:02}"

    return success({
        "session_id": session.id,
        "status": session.status.value if hasattr(session.status, "value") else str(session.status),
        "remaining_seconds": remaining_seconds,
        "remaining_time": remaining_time,
        "started_at": session.start_time.isoformat() if session.start_time else None,
        "expires_at": session.end_time.isoformat() if session.end_time else None,
        "mac_address": client.mac_address,
        "ip_address": client.current_ip,
        "pause_allowed": getattr(session, "pause_allowed", True),
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

    session = session_repo.get_active_session_by_client_id(client.id, for_update=True)
    if not session:
        return error("No active session")

    if not getattr(session, "pause_allowed", True):
        return error("Pause not allowed for this session package")

    now = get_utc_now()
    session.status = SessionStatus.PAUSED
    session.paused_at = now
    
    rem_sec = max(0, int((session.end_time - now).total_seconds()))
    session.remaining_seconds = rem_sec
    session.remaining_minutes = rem_sec // 60
    db.commit()

    if client.current_ip:
        firewall.remove(client.current_ip)

    return success({"session_id": session.id, "status": SessionStatus.PAUSED.value})

@router.post("/resume/{mac}")
def resume_session(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    client_repo = ClientRepository(db)
    session_repo = SessionRepository(db)
    firewall = FirewallService()

    client = client_repo.get_by_mac(validated.mac)
    if not client:
        return error("Client not found")

    session = session_repo.get_paused_session_by_client_id(client.id, for_update=True)
    if not session:
        return error("No paused session")

    if session.remaining_seconds is not None and session.remaining_seconds > 0:
        rem_sec = session.remaining_seconds
    else:
        rem_sec = (session.remaining_minutes or 0) * 60

    now = get_utc_now()
    session.status = SessionStatus.ACTIVE
    session.start_time = now
    session.end_time = now + timedelta(seconds=rem_sec)
    session.paused_at = None
    session.remaining_seconds = 0
    session.remaining_minutes = rem_sec // 60
    db.commit()

    if client.current_ip:
        firewall.authorize(client.current_ip)

    return success({"session_id": session.id, "status": SessionStatus.ACTIVE.value})