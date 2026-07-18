from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from services.firewall_service import FirewallService
import config
from api.v1.client import router as client_router
from api.v1.api import api_router
from core.exceptions import register_exception_handlers

from api.v1.session import router as session_router
from api.v1.voucher import router as voucher_router
from api.v1.coin import router as coin_router
from api.v1.health import router as health_router
from api.admin import router as admin_router
from scheduler.scheduler_service import SchedulerService
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logger = logging.getLogger(__name__)

    # Set up root tc qdiscs for bandwidth shaping (idempotent)
    try:
        from services.bandwidth_service import BandwidthService
        BandwidthService().setup()
    except Exception as exc:
        logger.warning("Bandwidth setup failed: %s", exc)

    # Wait for database to be available before running migrations
    try:
        from recovery.database_recovery import DatabaseRecovery
        DatabaseRecovery().wait_until_available()
    except Exception as exc:
        logger.warning("Database connection check failed: %s", exc)

    # Ensure all database migrations are applied (idempotent)
    try:
        from alembic.config import Config
        from alembic import command
        import os
        import sys
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.dirname(backend_dir))
        try:
            from installer.log_manager import get_logger
            mig_logger = get_logger("migration", "migration.log")
            mig_logger.info("Initializing database migrations...")
        except Exception:
            mig_logger = logger

        alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, "head")
        mig_logger.info("Database migrations applied successfully.")
        logger.info("Database migrations applied successfully.")
    except Exception as exc:
        logger.error("Failed to run database migrations: %s", exc)

    # Run startup recovery sequence
    from database import SessionLocal
    from recovery.database_recovery import DatabaseRecovery
    from recovery.power_recovery import PowerRecovery
    from recovery.session_recovery import SessionRecovery
    from recovery.firewall_recovery import FirewallRecovery
    from recovery.startup_sequence import StartupSequence
    from repositories.session_repository import SessionRepository
    from services.firewall_service import FirewallService

    db = SessionLocal()
    try:
        repo = SessionRepository(db)
        startup = StartupSequence(
            database_recovery=DatabaseRecovery(),
            power_recovery=PowerRecovery(repo, db),
            session_recovery=SessionRecovery(repo),
            firewall_recovery=FirewallRecovery(repo, FirewallService()),
        )
        startup.run()
    except Exception as exc:
        logger.error("Startup sequence failed: %s", exc)
    finally:
        db.close()

    scheduler = SchedulerService()
    scheduler.start()
    app.state.scheduler = scheduler

    # Pre-populate health cache synchronously on startup
    try:
        from services.admin_dashboard_service import AdminDashboardService, HealthCacheService, start_health_updater
        class MockRequest:
            def __init__(self, app):
                self.app = app
        db = SessionLocal()
        service = AdminDashboardService(db)
        data = service.get_system_health(MockRequest(app))
        HealthCacheService().set_cached_health(data)
        db.close()
        logger.info("Initial health cache pre-populated successfully.")
    except Exception as exc:
        logger.error("Failed to pre-populate initial health cache: %s", exc)

    # Start asynchronous background updater
    try:
        start_health_updater(app)
        logger.info("Background health cache updater started.")
    except Exception as exc:
        logger.error("Failed to start background health cache updater: %s", exc)

    yield

    # Cleanup background updater
    if hasattr(app.state, "health_updater_task"):
        app.state.health_updater_task.cancel()

    scheduler.stop()

app = FastAPI(
    title="PisoWiFi API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self' data:; "
        "frame-ancestors 'none';"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.include_router(health_router)
app.include_router(api_router)
app.include_router(session_router)
app.include_router(voucher_router)
app.include_router(coin_router)
app.include_router(client_router)
app.include_router(admin_router)
app.mount("/api/sfx", StaticFiles(directory=config.SFX_DIRECTORY), name="sfx")
register_exception_handlers(app)

@app.get("/")
def root():
    return {
        "success": True,
        "message": "PisoWiFi Backend Running"
    }
