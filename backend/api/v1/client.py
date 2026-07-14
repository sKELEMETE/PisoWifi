from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from schemas.validation import MacRequest

from database import get_db
from repositories.client_repository import ClientRepository
from services.network_service import NetworkService
from utils.api_response import success, error

router = APIRouter(prefix="/api/v1/client", tags=["Client"])

@router.get("")
def get_current_client(request: Request, db: Session = Depends(get_db)):
    network = NetworkService()
    ip_address = network.get_client_ip(request)
    mac_address = network.get_client_mac(ip_address)

    repo = ClientRepository(db)
    client = repo.get_by_mac(mac_address)

    if not client:
        client = repo.get_or_create(mac_address)

    old_ip = client.current_ip
    if old_ip and old_ip != ip_address:
        from repositories.session_repository import SessionRepository
        from services.firewall_service import FirewallService
        session_repo = SessionRepository(db)
        active_session = session_repo.get_active_session_by_client_id(client.id)
        if active_session:
            firewall = FirewallService()
            try:
                firewall.remove(old_ip)
            except Exception:
                pass
            try:
                firewall.authorize(ip_address)
            except Exception:
                pass

    client.current_ip = ip_address
    repo.update(client)

    is_online = client.status == "ONLINE"

    return success({
        "ip_address": ip_address,
        "mac_address": mac_address,
        "online": is_online,
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
