from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

import config
from database import get_db
from models.coin_reservation import CoinReservation, PendingCoin
from repositories.rate_repository import RateRepository
from repositories.client_repository import ClientRepository
from repositories.sales_repository import SalesRepository
from repositories.session_repository import SessionRepository
from services.session_service import SessionService
from services.coin_service import CoinService
from schemas.validation import MacRequest
from utils.api_response import success, error

router = APIRouter(prefix="/api/v1/coin", tags=["Coin"])

RESERVATION_TIMEOUT = config.COIN_RESERVATION_TIMEOUT


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _read_active_mac(db: Session) -> str | None:
    now = datetime.utcnow()
    res = db.query(CoinReservation).filter(CoinReservation.expires_at > now).first()
    return res.mac if res else None


def _is_reserved(db: Session) -> bool:
    now = datetime.utcnow()
    count = db.query(CoinReservation).filter(CoinReservation.expires_at > now).count()
    return count > 0


def _remaining_reservation_seconds(db: Session) -> int:
    now = datetime.utcnow()
    res = db.query(CoinReservation).filter(CoinReservation.expires_at > now).first()
    if not res:
        return 0
    delta = res.expires_at - now
    return max(0, int(delta.total_seconds()))


def get_pending_amount(db: Session, mac: str | None = None) -> int:
    if not mac:
        active_mac = _read_active_mac(db)
        if not active_mac:
            return 0
        mac = active_mac

    val = db.query(func.sum(PendingCoin.amount)).filter(PendingCoin.mac == mac).scalar()
    return int(val) if val is not None else 0


# ─────────────────────────────────────────────────────────────
# GET /status
# ─────────────────────────────────────────────────────────────

@router.get("/status")
def get_coin_status(db: Session = Depends(get_db)):
    reserved = _is_reserved(db)
    reserved_by = _read_active_mac(db) if reserved else None
    remaining = _remaining_reservation_seconds(db) if reserved else 0

    return success({
        "accepting": reserved,
        "reserved": reserved,
        "reserved_by": reserved_by,
        "remaining_seconds": remaining,
        "total_amount": get_pending_amount(db, reserved_by),
    })


# ─────────────────────────────────────────────────────────────
# POST /activate/{mac}
# ─────────────────────────────────────────────────────────────

@router.post("/activate/{mac}")
def activate_slot(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)

    # Enforce maximum concurrent connections
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
    now = datetime.utcnow()
    active_res = db.query(CoinReservation).filter(CoinReservation.expires_at > now).first()
    if active_res and active_res.mac != validated.mac:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": "Another customer is currently inserting coins. Please wait.",
            },
        )

    # Write reservation
    expires_at = now + timedelta(seconds=RESERVATION_TIMEOUT)
    if active_res:
        active_res.expires_at = expires_at
    else:
        db.query(CoinReservation).filter(CoinReservation.mac == validated.mac).delete()
        res = CoinReservation(mac=validated.mac, reserved_at=now, expires_at=expires_at)
        db.add(res)

    # Reset counters for this session
    db.query(PendingCoin).filter(PendingCoin.mac == validated.mac).delete()
    db.commit()

    return success({"status": "active", "remaining_seconds": RESERVATION_TIMEOUT})


# ─────────────────────────────────────────────────────────────
# POST /release/{mac}   (called by Done button or timeout finalize)
# ─────────────────────────────────────────────────────────────

@router.post("/release/{mac}")
def release_slot(mac: str, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)

    try:
        # Only the owner may release
        now = datetime.utcnow()
        active_res = db.query(CoinReservation).filter(CoinReservation.expires_at > now).first()
        if not active_res or active_res.mac != validated.mac:
            return error("Slot not reserved by this MAC")

        # Process accumulated coins
        pending_records = db.query(PendingCoin).filter(PendingCoin.mac == validated.mac).all()
        coins = [r.amount for r in pending_records]

        client_repository = ClientRepository(db)
        client = client_repository.get_by_mac(validated.mac)

        if coins:
            rate_repository = RateRepository(db)
            sales_repository = SalesRepository(db)
            session_repository = SessionRepository(db)
            session_service = SessionService(session_repository)
            coin_service = CoinService(
                rate_repository=rate_repository,
                client_repository=client_repository,
                session_service=session_service,
                sale_repository=sales_repository,
            )
            coin_service.process_coins_bulk(validated.mac, coins, authorize=False, commit=False)

        # Clean up reservation database records
        db.query(CoinReservation).filter(CoinReservation.mac == validated.mac).delete()
        db.query(PendingCoin).filter(PendingCoin.mac == validated.mac).delete()
        db.commit()

        if coins and client and client.current_ip:
            from services.firewall_service import FirewallService
            FirewallService().authorize(client.current_ip)

    except Exception as e:
        db.rollback()
        return error(f"Failed to release: {str(e)}")

    return success({"status": "released"})


# ─────────────────────────────────────────────────────────────
# POST /insert   (called by hardware serial listener)
# ─────────────────────────────────────────────────────────────

@router.post("/insert")
def insert_coin(value: int, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    active_res = db.query(CoinReservation).filter(CoinReservation.expires_at > now).first()
    if not active_res:
        return error("No active slot reservation found.")

    # 1. Insert pending coin record
    coin = PendingCoin(mac=active_res.mac, amount=value, created_at=now)
    db.add(coin)

    # 2. Extend reservation window
    active_res.expires_at = now + timedelta(seconds=RESERVATION_TIMEOUT)
    db.commit()

    return success({
        "coin": value,
        "mac": active_res.mac,
        "status": "accumulated",
        "remaining_seconds": max(0, int((active_res.expires_at - now).total_seconds())),
    })


# ─────────────────────────────────────────────────────────────
# POST /test/{mac}/{value}   (development / hardware-less testing)
# ─────────────────────────────────────────────────────────────

@router.post("/test/{mac}/{value}")
def test_coin(mac: str, value: int, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    now = datetime.utcnow()
    active_res = db.query(CoinReservation).filter(CoinReservation.expires_at > now).first()
    if not active_res or active_res.mac != validated.mac:
        return error("Slot not active or reserved by another MAC")

    # Insert pending coin record
    coin = PendingCoin(mac=validated.mac, amount=value, created_at=now)
    db.add(coin)

    # Extend reservation window
    active_res.expires_at = now + timedelta(seconds=RESERVATION_TIMEOUT)
    db.commit()

    return success({
        "coin": value,
        "status": "accumulated",
        "remaining_seconds": max(0, int((active_res.expires_at - now).total_seconds())),
    })