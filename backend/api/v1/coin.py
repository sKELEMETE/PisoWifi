from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os

from database import get_db
from repositories.rate_repository import RateRepository
from repositories.client_repository import ClientRepository
from repositories.sales_repository import SalesRepository
from repositories.session_repository import SessionRepository
from services.session_service import SessionService
from services.coin_service import CoinService
from schemas.validation import MacRequest, CoinRequest
from utils.api_response import success, error

router = APIRouter(prefix="/api/v1/coin", tags=["Coin"])

def get_pending_amount():
    try:
        with open("/tmp/pending_coin.txt", "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0

@router.get("/status")
def get_coin_status():
    amount = get_pending_amount()
    return success({
        "accepting": True,
        "total_amount": amount,
        "last_coin": 0,
    })

@router.post("/activate/{mac}")
def activate_slot(mac: str):

    import traceback

    try:
        with open("/tmp/test_write.txt", "w") as f:
            f.write("hello")
    except Exception:
        traceback.print_exc()

    validated = MacRequest(mac=mac)

    print("WRITING ACTIVE MAC:", validated.mac)

    with open("/tmp/active_mac.txt", "w") as f:
        f.write(validated.mac)
        f.flush()
        os.fsync(f.fileno())

    return success({"status": "active"})

@router.get("/{mac}")
def coin_status(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    client_repo = ClientRepository(db)
    client = client_repo.get_by_mac(validated.mac)

    if not client:
        return error("Client not found")

    return success({
        "client_id": client.id,
        "status": client.status,
        "ip": client.current_ip,
    })

@router.post("/test/{mac}/{value}")
def test_coin(mac: str, value: int, db: Session = Depends(get_db)):
    validated_mac = MacRequest(mac=mac)
    validated_coin = CoinRequest(value=value)

    rate_repository = RateRepository(db)
    client_repository = ClientRepository(db)
    sales_repository = SalesRepository(db)
    session_repository = SessionRepository(db)
    session_service = SessionService(session_repository)

    coin_service = CoinService(
        rate_repository=rate_repository,
        client_repository=client_repository,
        session_service=session_service,
        sale_repository=sales_repository,
    )

    session = coin_service.process_coin(
        validated_mac.mac,
        validated_coin.value,
    )

    if not session:
        return error("Coin could not be processed")

    return success({
        "session_id": session.id,
        "client_id": session.client_id,
        "coin": validated_coin.value,
        "minutes_added": validated_coin.value,
        "status": "processed",
    })
