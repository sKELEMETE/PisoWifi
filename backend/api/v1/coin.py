import json
import os
import fcntl
import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from repositories.rate_repository import RateRepository
from repositories.client_repository import ClientRepository
from repositories.sales_repository import SalesRepository
from repositories.session_repository import SessionRepository
from services.session_service import SessionService
from services.coin_service import CoinService
from schemas.validation import MacRequest
from utils.api_response import success, error

router = APIRouter(prefix="/api/v1/coin", tags=["Coin"])

ACTIVE_MAC_FILE = "/tmp/active_mac.txt"
PENDING_COIN_FILE = "/tmp/pending_coin.txt"
RESERVATION_TIMEOUT = 30  # seconds


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _read_active_mac() -> str | None:
    try:
        with open(ACTIVE_MAC_FILE, "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            mac = f.read().strip()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return mac if mac else None
    except FileNotFoundError:
        return None


def _reservation_age() -> float | None:
    """Return seconds since active_mac.txt was last touched, or None if absent."""
    try:
        return time.time() - os.path.getmtime(ACTIVE_MAC_FILE)
    except FileNotFoundError:
        return None


def _is_reserved() -> bool:
    age = _reservation_age()
    return age is not None and age < RESERVATION_TIMEOUT


def _remaining_reservation_seconds() -> int:
    age = _reservation_age()
    if age is None or age >= RESERVATION_TIMEOUT:
        return 0
    return max(0, int(RESERVATION_TIMEOUT - age))


def get_pending_amount() -> int:
    try:
        with open(PENDING_COIN_FILE, "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            val = int(f.read().strip())
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return val
    except (FileNotFoundError, ValueError):
        return 0


# ─────────────────────────────────────────────────────────────
# GET /status
# ─────────────────────────────────────────────────────────────

@router.get("/status")
def get_coin_status():
    reserved = _is_reserved()
    reserved_by = _read_active_mac() if reserved else None
    remaining = _remaining_reservation_seconds() if reserved else 0
    return success({
        "accepting": reserved,
        "reserved": reserved,
        "reserved_by": reserved_by,
        "remaining_seconds": remaining,
        "total_amount": get_pending_amount(),
    })


# ─────────────────────────────────────────────────────────────
# POST /activate/{mac}
# ─────────────────────────────────────────────────────────────

@router.post("/activate/{mac}")
def activate_slot(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    coins_file = f"/tmp/session_coins_{validated.mac}.json"

    # Enforce maximum concurrent connections to prevent kernel memory exhaustion
    client_repo = ClientRepository(db)
    session_repo = SessionRepository(db)
    client = client_repo.get_by_mac(validated.mac)
    
    has_active = False
    if client:
        active_session = session_repo.get_active_session_by_client_id(client.id)
        if active_session:
            has_active = True

    if not has_active:
        active_count = session_repo.count_active_sessions()
        if active_count >= 150:
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "message": "Network is at full capacity. Please try again later.",
                },
            )

    # Enforce exclusive reservation
    if _is_reserved():
        current_owner = _read_active_mac()
        if current_owner and current_owner != validated.mac:
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "message": "Another customer is currently inserting coins. Please wait.",
                },
            )

    # Write reservation
    with open(ACTIVE_MAC_FILE, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(validated.mac)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Reset counters for this session
    try:
        with open(PENDING_COIN_FILE, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write("0")
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        if os.path.exists(coins_file):
            os.remove(coins_file)
    except Exception:
        pass

    return success({"status": "active", "remaining_seconds": RESERVATION_TIMEOUT})


# ─────────────────────────────────────────────────────────────
# POST /release/{mac}   (called by Done button or timeout finalize)
# ─────────────────────────────────────────────────────────────

@router.post("/release/{mac}")
def release_slot(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    coins_file = f"/tmp/session_coins_{validated.mac}.json"

    try:
        # Only the owner may release
        current_owner = _read_active_mac()
        if current_owner != validated.mac:
            return error("Slot not reserved by this MAC")

        # Process accumulated coins → create/extend session → authorize internet
        coins: list[int] = []
        if os.path.exists(coins_file):
            try:
                with open(coins_file, "r") as f:
                    coins = json.load(f)
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
            # Process all coins except the last without calling firewall subprocesses.
            # Perform single final authorization on the last processed coin.
            for i, coin_val in enumerate(coins):
                is_last = (i == len(coins) - 1)
                coin_service.process_coin(validated.mac, coin_val, authorize=is_last)

        # Clean up reservation files
        for path in (ACTIVE_MAC_FILE, PENDING_COIN_FILE, coins_file):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    except Exception as e:
        return error(f"Failed to release: {str(e)}")

    return success({"status": "released"})


# ─────────────────────────────────────────────────────────────
# POST /test/{mac}/{value}   (development / hardware-less testing)
# ─────────────────────────────────────────────────────────────

@router.post("/test/{mac}/{value}")
def test_coin(mac: str, value: int):
    validated_mac = MacRequest(mac=mac)
    coins_file = f"/tmp/session_coins_{validated_mac.mac}.json"

    if not _is_reserved():
        return error("Slot not active")

    current_owner = _read_active_mac()
    if current_owner != validated_mac.mac:
        return error("Slot not active or reserved by another MAC")

    # Update pending total
    current = get_pending_amount()
    with open(PENDING_COIN_FILE, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(str(current + value))
        f.flush()
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Append to coin list
    coins: list[int] = []
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

    # Touch active_mac.txt to extend reservation window
    try:
        os.utime(ACTIVE_MAC_FILE, None)
    except Exception:
        pass

    return success({
        "coin": value,
        "status": "accumulated",
        "remaining_seconds": _remaining_reservation_seconds(),
    })