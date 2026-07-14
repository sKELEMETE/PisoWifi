from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os
import fcntl

from database import get_db
from repositories.rate_repository import RateRepository
from repositories.client_repository import ClientRepository
from repositories.sales_repository import SalesRepository
from repositories.session_repository import SessionRepository
from services.session_service import SessionService
from services.coin_service import CoinService
from schemas.validation import MacRequest, CoinRequest
from utils.api_response import success, error

import time

router = APIRouter(prefix="/api/v1/coin", tags=["Coin"])

def get_pending_amount():
    try:
        with open("/tmp/pending_coin.txt", "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            val = int(f.read().strip())
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return val
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
    validated = MacRequest(mac=mac)
    active_mac_file = "/tmp/active_mac.txt"
    pending_coin_file = "/tmp/pending_coin.txt"
    coins_file = f"/tmp/session_coins_{validated.mac}.json"

    # Enforce reservation check
    try:
        if os.path.exists(active_mac_file):
            mtime = os.path.getmtime(active_mac_file)
            if time.time() - mtime < 30:
                with open(active_mac_file, "r") as f:
                    current_active = f.read().strip()
                if current_active and current_active != validated.mac:
                    return error("Another customer is currently using the coin slot. Please wait.")
    except Exception:
        pass

    # Activate slot by writing current MAC
    with open(active_mac_file, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(validated.mac)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Reset pending coins and session coin list for the new session
    try:
        with open(pending_coin_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write("0")
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        if os.path.exists(coins_file):
            os.remove(coins_file)
    except Exception:
        pass

    return success({"status": "active"})

@router.post("/release/{mac}")
def release_slot(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    active_mac_file = "/tmp/active_mac.txt"
    pending_coin_file = "/tmp/pending_coin.txt"
    coins_file = f"/tmp/session_coins_{validated.mac}.json"
    try:
        if os.path.exists(active_mac_file):
            with open(active_mac_file, "r") as f:
                current_active = f.read().strip()
            if current_active == validated.mac:
                # Process all accumulated coins individually
                import json
                coins = []
                if os.path.exists(coins_file):
                    try:
                        with open(coins_file, "r") as f_coins:
                            coins = json.load(f_coins)
                    except Exception:
                        pass

                if coins:
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

                    for coin_val in coins:
                        coin_service.process_coin(validated.mac, coin_val)

                # Cleanup temp files
                os.remove(active_mac_file)
                if os.path.exists(pending_coin_file):
                    os.remove(pending_coin_file)
                if os.path.exists(coins_file):
                    os.remove(coins_file)
    except Exception as e:
        return error(f"Failed to release: {str(e)}")
    return success({"status": "released"})


@router.post("/test/{mac}/{value}")
def test_coin(mac: str, value: int):
    validated_mac = MacRequest(mac=mac)
    active_mac_file = "/tmp/active_mac.txt"
    pending_coin_file = "/tmp/pending_coin.txt"
    coins_file = f"/tmp/session_coins_{validated_mac.mac}.json"

    # Enforce active check
    try:
        if os.path.exists(active_mac_file):
            with open(active_mac_file, "r") as f:
                current_active = f.read().strip()
            if current_active != validated_mac.mac:
                return error("Slot not active or reserved by another MAC")
        else:
            return error("Slot not active")
    except Exception:
        return error("Slot check failed")

    # Update pending amount
    current = 0
    try:
        if os.path.exists(pending_coin_file):
            with open(pending_coin_file, "r") as f:
                content = f.read().strip()
                if content:
                    current = int(content)
    except Exception:
        pass

    with open(pending_coin_file, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(str(current + value))
        f.flush()
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Append to JSON coins list
    import json
    coins = []
    try:
        if os.path.exists(coins_file):
            with open(coins_file, "r") as f:
                coins = json.load(f)
    except Exception:
        pass
    
    coins.append(value)
    with open(coins_file, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(coins, f)
        f.flush()
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Touch active_mac.txt to extend reservation
    try:
        os.utime(active_mac_file, None)
    except Exception:
        pass

    return success({
        "coin": value,
        "status": "accumulated",
    })