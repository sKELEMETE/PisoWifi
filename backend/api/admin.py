from fastapi import APIRouter, Depends, Response, Request, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
import config
from database import get_db
from utils.api_response import success, error
from utils.auth import create_access_token, get_current_admin, verify_password
from utils.rate_limiter import login_limiter
from services.admin_dashboard_service import AdminDashboardService

router = APIRouter(prefix="/api/admin", tags=["Admin"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(request: Request, payload: LoginRequest, response: Response):
    client_ip = request.client.host if request.client else "unknown"

    # Check lockout first
    is_locked, remaining = login_limiter.is_locked(client_ip)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Locked for {remaining} seconds."
        )

    # Perform strict verification using bcrypt hash helper
    if payload.username != config.ADMIN_USERNAME or not verify_password(payload.password):
        login_limiter.record_failure(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Successful login resets the counter
    login_limiter.reset(client_ip)

    # Generate token
    token = create_access_token(payload.username)
    
    # Secure Cookie settings
    is_secure = request.url.scheme == "https"
    
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=config.ADMIN_TOKEN_EXPIRE_HOURS * 3600
    )
    
    return success(message="Login successful")

@router.post("/logout")
def logout(request: Request, response: Response, current_admin: str = Depends(get_current_admin)):
    is_secure = request.url.scheme == "https"
    response.delete_cookie(
        key="admin_token",
        httponly=True,
        samesite="lax",
        secure=is_secure
    )
    return success(message="Logout successful")

@router.get("/check")
def check_auth(current_admin: str = Depends(get_current_admin)):
    return success(data={"username": current_admin}, message="Authenticated")

@router.get("/dashboard")
def get_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin)
):
    service = AdminDashboardService(db)
    sales = service.get_sales_data()
    active_users = service.get_active_users()
    system_health = service.get_system_health(request)

    dashboard_data = {
        "sales": sales,
        "active_users": active_users,
        "system_health": system_health
    }
    return success(data=dashboard_data, message="Dashboard compiled successfully")
