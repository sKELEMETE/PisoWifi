from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from database import get_db
from models.session import Session as SessionModel
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
        active_count = db.execute(
            select(func.count()).select_from(SessionModel).where(SessionModel.status == "ACTIVE")
        ).scalar_one()

        paused_count = db.execute(
            select(func.count()).select_from(SessionModel).where(SessionModel.status == "PAUSED")
        ).scalar_one()

        status["database"] = True
        status["active_sessions"] = active_count
        status["paused_sessions"] = paused_count
        status["sessions"] = active_count + paused_count

    except Exception:
        return {
            "success": False,
            "message": "System unhealthy",
            "data": status
        }

    return success(status)
