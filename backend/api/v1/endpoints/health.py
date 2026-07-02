from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {
        "success": True,
        "message": "System Healthy",
        "data": {
            "database": "healthy",
            "firewall": "healthy",
            "serial": "healthy",
            "network": "healthy"
        }
    }
