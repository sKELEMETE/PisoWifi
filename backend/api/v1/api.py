from fastapi import APIRouter

from api.v1.endpoints.health import router as health_router

api_router = APIRouter(
    prefix="/api/v1"
)

api_router.include_router(
    health_router,
    tags=["Health"]
)
