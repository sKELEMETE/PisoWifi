from fastapi import APIRouter

from api.v1.endpoints.health import router as health_router
from api.v1.pricing import router as pricing_router
from api.v1.voucher import router as voucher_router

api_router = APIRouter(
    prefix="/api/v1"
)

api_router.include_router(
    health_router,
    tags=["Health"]
)

api_router.include_router(voucher_router)
api_router.include_router(pricing_router)
