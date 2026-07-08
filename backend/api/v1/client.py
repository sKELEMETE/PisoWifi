from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.validation import MacRequest

from database import get_db
from repositories.client_repository import ClientRepository
from utils.api_response import success, error

router = APIRouter(prefix="/api/v1/client", tags=["Client"])

@router.get("")
def get_current_client(db: Session = Depends(get_db)):

    return success({
        "ip_address": None,
        "mac_address": None,
        "online": False,
    })

@router.get("/{mac}")
def get_client(mac: str, db: Session = Depends(get_db)):

    validated = MacRequest(mac=mac)

    repo = ClientRepository(db)

    client = repo.get_by_mac(validated.mac)

    if not client:
        return error("Client not found", ["MAC does not exist"])

    return success({
        "id": client.id,
        "mac": client.mac_address,
        "ip": client.current_ip,
        "status": client.status,
    })
