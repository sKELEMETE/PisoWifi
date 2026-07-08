from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from repositories.session_repository import SessionRepository

from utils.api_response import success

router = APIRouter(prefix="/api/v1/health", tags=["Health"])

@router.get("")
def health(db: Session = Depends(get_db)):

    status = {
        "database": False,
        "sessions": 0,
        "active_sessions": 0,
        "paused_sessions": 0,
    }

    try:
        repo = SessionRepository(db)

        active = repo.get_active_sessions()
        paused = repo.get_paused_sessions()

        status["database"] = True
        status["active_sessions"] = len(active)
        status["paused_sessions"] = len(paused)
        status["sessions"] = len(active) + len(paused)

    except Exception:
        return {
            "success": False,
            "message": "System unhealthy",
            "data": status
        }

    return success(status)
