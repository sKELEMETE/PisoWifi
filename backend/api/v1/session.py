from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta
from database import get_db
from models.client import Client
from models.session import Session as SessionModel, SessionStatus, ClientLiveSession
from repositories.session_repository import SessionRepository
from repositories.client_repository import ClientRepository
from services.session_service import SessionService
from services.client_service import ClientService
from schemas.validation import MacRequest
from utils.api_response import success, error
from utils.time_utils import get_utc_now

router = APIRouter(prefix="/api/v1/session", tags=["Session"])


def _format_session_response(client: Client, session: SessionModel) -> dict:
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

    return {
        "session_id": session.id,
        "status": session.status.value if hasattr(session.status, "value") else str(session.status),
        "remaining_seconds": remaining_seconds,
        "remaining_time": remaining_time,
        "started_at": session.start_time.isoformat() if session.start_time else None,
        "expires_at": session.end_time.isoformat() if session.end_time else None,
        "mac_address": client.mac_address,
        "ip_address": client.current_ip,
        "pause_allowed": getattr(session, "pause_allowed", True),
    }


@router.get("/current")
@router.get("")
def get_current_session(request: Request, db: Session = Depends(get_db)):
    client_service = ClientService(ClientRepository(db))
    client = client_service.resolve_trusted_client(request)

    live = db.query(ClientLiveSession).filter(ClientLiveSession.client_id == client.id).first()
    session = None
    if live:
        session = db.query(SessionModel).filter(SessionModel.id == live.session_id).first()

    if not session or session.status not in (SessionStatus.ACTIVE, SessionStatus.PAUSED):
        return error("No active session", ["Session missing"])

    return success(_format_session_response(client, session))


@router.get("/{mac}")
def get_session(mac: str, request: Request, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    client_service = ClientService(ClientRepository(db))
    # Identity verification: verify caller is the actual owner of this MAC
    client = client_service.resolve_trusted_client(request, claimed_mac=validated.mac)

    stmt = (
        select(Client, SessionModel)
        .outerjoin(
            SessionModel,
            (SessionModel.client_id == Client.id) & SessionModel.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED])
        )
        .where(Client.mac_address == client.mac_address)
        .order_by(SessionModel.id.desc())
    )
    row = db.execute(stmt).first()

    if not row:
        return error("Client not found", ["MAC invalid"])

    client_row, session = row
    if not session:
        return error("No active session", ["Session missing"])

    return success(_format_session_response(client_row, session))


@router.post("/pause")
def pause_current_session(request: Request, db: Session = Depends(get_db)):
    client_service = ClientService(ClientRepository(db))
    client = client_service.resolve_trusted_client(request)
    session_service = SessionService(SessionRepository(db))
    try:
        session = session_service.pause_session(client.id)
        return success({"session_id": session.id, "status": SessionStatus.PAUSED.value})
    except ValueError as exc:
        return error(str(exc))


@router.post("/pause/{mac}")
def pause_session(mac: str, request: Request, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    client_service = ClientService(ClientRepository(db))
    client = client_service.resolve_trusted_client(request, claimed_mac=validated.mac)
    session_service = SessionService(SessionRepository(db))
    try:
        session = session_service.pause_session(client.id)
        return success({"session_id": session.id, "status": SessionStatus.PAUSED.value})
    except ValueError as exc:
        return error(str(exc))


@router.post("/resume")
def resume_current_session(request: Request, db: Session = Depends(get_db)):
    client_service = ClientService(ClientRepository(db))
    client = client_service.resolve_trusted_client(request)
    session_service = SessionService(SessionRepository(db))
    try:
        session = session_service.resume_session(client.id)
        return success({"session_id": session.id, "status": SessionStatus.ACTIVE.value})
    except ValueError as exc:
        return error(str(exc))


@router.post("/resume/{mac}")
def resume_session(mac: str, request: Request, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    client_service = ClientService(ClientRepository(db))
    client = client_service.resolve_trusted_client(request, claimed_mac=validated.mac)
    session_service = SessionService(SessionRepository(db))
    try:
        session = session_service.resume_session(client.id)
        return success({"session_id": session.id, "status": SessionStatus.ACTIVE.value})
    except ValueError as exc:
        return error(str(exc))