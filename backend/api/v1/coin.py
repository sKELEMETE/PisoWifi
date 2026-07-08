from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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


@router.get("/status")
def get_coin_status():

    return success({
        "accepting": True,
        "total_amount": 0,
        "last_coin": 0,
    })


@router.get("/{mac}")
def coin_status(mac: str, db: Session = Depends(get_db)):

    validated = MacRequest(mac=mac)
    mac = validated.mac

    client_repo = ClientRepository(db)

    client = client_repo.get_by_mac(mac)

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

    mac = validated_mac.mac
    value = validated_coin.value

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
        mac,
        value,
    )

    if not session:
        return error("Coin could not be processed")

    return success({
        "session_id": session.id,
        "client_id": session.client_id,
        "coin": value,
        "minutes_added": value,
        "status": "processed",
    })
