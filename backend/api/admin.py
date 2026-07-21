import logging
from fastapi import APIRouter, Depends, Response, Request, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
import config
from database import get_db
from utils.api_response import success, error
from utils.auth import create_access_token, get_current_admin, verify_password, generate_csrf_token
from utils.rate_limiter import login_limiter
from services.admin_dashboard_service import AdminDashboardService, HealthCacheService
from services.admin_credentials_service import AdminCredentialsService
from services.network_service import NetworkService

router = APIRouter(prefix="/api/admin", tags=["Admin"])
logger = logging.getLogger("auth_api")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(request: Request, payload: LoginRequest, response: Response):
    client_ip = NetworkService().get_client_ip(request)
    limiter_key = f"{client_ip}:{payload.username}"

    # Check lockout first by IP and combined key
    is_locked_ip, remaining_ip = login_limiter.is_locked(client_ip)
    is_locked_key, remaining_key = login_limiter.is_locked(limiter_key)
    if is_locked_ip or is_locked_key:
        remaining = max(remaining_ip, remaining_key)
        logger.warning("Admin login blocked due to rate limit lockout for IP %s / user %s (remaining: %ds)", client_ip, payload.username, remaining)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Locked for {remaining} seconds."
        )

    # Perform strict verification using bcrypt hash helper
    if payload.username != config.ADMIN_USERNAME or not verify_password(payload.password):
        login_limiter.record_failure(client_ip)
        login_limiter.record_failure(limiter_key)
        logger.warning("Admin login failed for user '%s' from IP %s", payload.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Successful login resets the counter
    login_limiter.reset(client_ip)
    login_limiter.reset(limiter_key)

    # Generate token
    token = create_access_token(payload.username)
    
    # Secure Cookie settings
    is_secure = request.url.scheme == "https"
    
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        samesite="strict",
        secure=is_secure,
        max_age=config.ADMIN_TOKEN_EXPIRE_HOURS * 3600,
        path="/",
    )

    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        samesite="strict",
        secure=is_secure,
        max_age=config.ADMIN_TOKEN_EXPIRE_HOURS * 3600,
        path="/",
    )
    
    logger.info("Admin login successful for user '%s' from IP %s", payload.username, client_ip)
    return success(data={"csrf_token": csrf_token}, message="Login successful")


@router.post("/logout")
def logout(request: Request, response: Response, current_admin: str = Depends(get_current_admin)):
    is_secure = request.url.scheme == "https"
    response.delete_cookie(
        key="admin_token",
        httponly=True,
        samesite="strict",
        secure=is_secure,
        path="/",
    )
    response.delete_cookie(
        key="csrf_token",
        httponly=False,
        samesite="strict",
        secure=is_secure,
        path="/",
    )
    logger.info("Admin logout executed for user '%s'", current_admin)
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
    system_health = HealthCacheService().get_cached_health()
    if system_health is None:
        system_health = service.get_system_health(request)

    dashboard_data = {
        "sales": sales,
        "active_users": active_users,
        "system_health": system_health
    }
    return success(data=dashboard_data, message="Dashboard compiled successfully")


class ChangeCredentialsRequest(BaseModel):
    current_password: str
    new_username: str | None = None
    new_password: str | None = None


@router.post("/credentials")
def change_credentials(
    request: Request,
    payload: ChangeCredentialsRequest,
    response: Response,
    current_admin: str = Depends(get_current_admin)
):
    try:
        result = AdminCredentialsService.change_credentials(
            current_password=payload.current_password,
            new_username=payload.new_username,
            new_password=payload.new_password
        )
        is_secure = request.url.scheme == "https"
        # Invalidate active session cookie to force re-login with updated credentials
        response.delete_cookie(
            key="admin_token",
            httponly=True,
            samesite="strict",
            secure=is_secure,
            path="/",
        )
        response.delete_cookie(
            key="csrf_token",
            httponly=False,
            samesite="strict",
            secure=is_secure,
            path="/",
        )
        return success(
            data=result,
            message="Credentials updated successfully. Session invalidated. Please log in again."
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )

