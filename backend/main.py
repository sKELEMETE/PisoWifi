from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.firewall_service import FirewallService
from api.v1.client import router as client_router
from api.v1.api import api_router
from core.exceptions import register_exception_handlers

from api.v1.session import router as session_router
from api.v1.voucher import router as voucher_router
from api.v1.coin import router as coin_router
from api.v1.health import router as health_router
from scheduler.scheduler_service import SchedulerService

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    scheduler = SchedulerService()
    scheduler.start()
    yield
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

app.include_router(health_router)
app.include_router(api_router)
app.include_router(session_router)
app.include_router(voucher_router)
app.include_router(coin_router)
app.include_router(client_router)
register_exception_handlers(app)

@app.get("/")
def root():
    return {
        "success": True,
        "message": "PisoWiFi Backend Running"
    }
