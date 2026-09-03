from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from database import get_db
from models.session import Session as SessionModel, SessionStatus
from utils.api_response import success
from utils.auth import get_current_admin
from services.health_service import HealthService

router = APIRouter(tags=["Health"])


@router.get("/live")
def liveness():
    """Liveness probe: returns 200 if the process is responsive."""
    return HealthService().check_liveness()


@router.get("/ready")
def readiness(response: Response, db: Session = Depends(get_db)):
    """Readiness probe: verifies DB, firewall, and hardware dependencies."""
    is_ready, details = HealthService().check_readiness(db)
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return details


@router.get("/admin")
def admin_diagnostics(db: Session = Depends(get_db), current_user: str = Depends(get_current_admin)):
    """Deep diagnostic probe for administrative telemetry."""
    return HealthService().check_admin_diagnostics(db)


@router.get("")
def health(db: Session = Depends(get_db)):
    """Legacy health endpoint."""
    status_data = {
        "database": False,
        "sessions": 0,
        "active_sessions": 0,
        "paused_sessions": 0,
    }

    try:
        active_count = db.execute(
            select(func.count()).select_from(SessionModel).where(SessionModel.status == SessionStatus.ACTIVE)
        ).scalar_one()

        paused_count = db.execute(
            select(func.count()).select_from(SessionModel).where(SessionModel.status == SessionStatus.PAUSED)
        ).scalar_one()

        status_data["database"] = True
        status_data["active_sessions"] = active_count
        status_data["paused_sessions"] = paused_count
        status_data["sessions"] = active_count + paused_count

    except Exception:
        return {
            "success": False,
            "message": "System unhealthy",
            "data": status_data
        }

    return success(status_data)
