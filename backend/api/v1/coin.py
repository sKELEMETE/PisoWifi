from __future__ import annotations

from datetime import timedelta
import logging
import secrets
import threading
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

import config
from database import get_db
from models.coin_reservation import CoinReservation, PendingCoin
from repositories.client_repository import ClientRepository
from repositories.rate_repository import RateRepository
from repositories.sales_repository import SalesRepository
from repositories.session_repository import SessionRepository
from schemas.validation import CoinLeaseRequest, MacRequest
from services.coin_service import CoinService
from services.hardware_service import hardware_service
from services.network_service import NetworkService
from services.session_service import SessionService
from utils.api_response import error, success
from utils.time_utils import get_utc_now

router = APIRouter(prefix="/api/v1/coin", tags=["Coin"])
logger = logging.getLogger(__name__)
_activation_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    return NetworkService().get_client_ip(request)


def _masked_mac(mac: str) -> str:
    return f"**:**:**:**:{mac[-5:]}"


def _active_reservation(db: Session, lock: bool = False) -> CoinReservation | None:
    query = db.query(CoinReservation).filter(CoinReservation.expires_at > get_utc_now())
    if lock:
        query = query.with_for_update()
    return query.first()


def _valid_owner(reservation: CoinReservation | None, mac: str, token: str, ip: str) -> bool:
    return bool(
        reservation
        and reservation.mac == mac
        and secrets.compare_digest(reservation.lease_id or "", token)
        and (not reservation.owner_ip or reservation.owner_ip == ip)
    )


def get_pending_amount(db: Session, mac: str) -> int:
    value = db.query(func.sum(PendingCoin.amount)).filter(PendingCoin.mac == mac).scalar()
    return int(value) if value is not None else 0


def _coin_service(db: Session) -> CoinService:
    return CoinService(
        rate_repository=RateRepository(db),
        client_repository=ClientRepository(db),
        session_service=SessionService(SessionRepository(db)),
        sale_repository=SalesRepository(db),
    )


@router.get("/status")
def get_coin_status(
    mac: str,
    request: Request,
    lease_token: Annotated[str, Header(alias="X-Coin-Lease")],
    db: Session = Depends(get_db),
):
    validated = MacRequest(mac=mac)
    reservation = _active_reservation(db)
    if not _valid_owner(reservation, validated.mac, lease_token, _client_ip(request)):
        return JSONResponse(status_code=409, content={"success": False, "message": "Coin session is no longer active."})
    remaining = max(0, int((reservation.expires_at - get_utc_now()).total_seconds()))
    return success({
        "accepting": True,
        "remaining_seconds": remaining,
        "total_amount": get_pending_amount(db, validated.mac),
    })


@router.post("/activate/{mac}")
def activate_slot(mac: str, request: Request, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    owner_ip = _client_ip(request)
    client_repo = ClientRepository(db)
    session_repo = SessionRepository(db)
    client = client_repo.get_by_mac(validated.mac)
    if not client or client.current_ip != owner_ip:
        return JSONResponse(status_code=403, content={"success": False, "message": "Customer identity could not be verified."})

    active_session = session_repo.get_active_session_by_client_id(client.id)
    if not active_session and session_repo.count_active_sessions() >= 150:
        return JSONResponse(status_code=409, content={"success": False, "message": "Network is at full capacity. Please try again later."})

    with _activation_lock:
        try:
            now = get_utc_now()
            reservations = db.query(CoinReservation).with_for_update().all()
            active = next((item for item in reservations if item.expires_at > now), None)
            if active and active.mac != validated.mac:
                db.rollback()
                return JSONResponse(status_code=409, content={"success": False, "message": "Another customer is currently inserting coins. Please wait."})

            if active:
                if active.owner_ip and active.owner_ip != owner_ip:
                    db.rollback()
                    return JSONResponse(status_code=409, content={"success": False, "message": "This customer's coin session is active on another connection."})
                lease_token = active.lease_id or secrets.token_urlsafe(32)
                active.lease_id = lease_token
                active.owner_ip = owner_ip
                active.last_heartbeat_at = now
                active.expires_at = now + timedelta(seconds=config.COIN_SESSION_LEASE_SECONDS)
            else:
                lease_token = secrets.token_urlsafe(32)
                db.query(CoinReservation).delete()
                db.query(PendingCoin).filter(PendingCoin.mac == validated.mac).delete()
                db.add(CoinReservation(
                    mac=validated.mac,
                    reserved_at=now,
                    expires_at=now + timedelta(seconds=config.COIN_SESSION_LEASE_SECONDS),
                    lease_id=lease_token,
                    owner_ip=owner_ip,
                    last_heartbeat_at=now,
                ))
            db.commit()
            hardware_service.set_accepting(True)
        except Exception as exc:
            db.rollback()
            try:
                db.query(CoinReservation).filter(CoinReservation.mac == validated.mac).delete()
                db.commit()
            except Exception:
                db.rollback()
            try:
                hardware_service.set_accepting(False)
            except Exception as off_exc:
                logger.critical("Unable to assert coin relay OFF after activation failure: %s", off_exc)
            logger.error("Failed to activate coin hardware: %s", exc)
            return JSONResponse(status_code=503, content={"success": False, "message": "Coin hardware is unavailable."})

    logger.info("Coin session started for %s", _masked_mac(validated.mac))
    return success({
        "status": "active",
        "lease_token": lease_token,
        "lease_seconds": config.COIN_SESSION_LEASE_SECONDS,
        "heartbeat_seconds": config.COIN_HEARTBEAT_SECONDS,
    })


@router.post("/heartbeat/{mac}")
def heartbeat_slot(mac: str, body: CoinLeaseRequest, request: Request, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    reservation = _active_reservation(db, lock=True)
    if not _valid_owner(reservation, validated.mac, body.lease_token, _client_ip(request)):
        return JSONResponse(status_code=409, content={"success": False, "message": "Coin session is no longer active."})
    now = get_utc_now()
    reservation.last_heartbeat_at = now
    reservation.expires_at = now + timedelta(seconds=config.COIN_SESSION_LEASE_SECONDS)
    db.commit()
    return success({"remaining_seconds": config.COIN_SESSION_LEASE_SECONDS})


@router.post("/release/{mac}")
def release_slot(mac: str, body: CoinLeaseRequest, request: Request, db: Session = Depends(get_db)):
    validated = MacRequest(mac=mac)
    reservation = _active_reservation(db, lock=True)
    if not _valid_owner(reservation, validated.mac, body.lease_token, _client_ip(request)):
        return JSONResponse(status_code=409, content={"success": False, "message": "Coin session is no longer active."})

    hardware_service.set_accepting(False)
    try:
        coins = [record.amount for record in db.query(PendingCoin).filter(PendingCoin.mac == validated.mac).all()]
        client = ClientRepository(db).get_by_mac(validated.mac)
        if coins:
            _coin_service(db).process_coins_bulk(validated.mac, coins, authorize=False, commit=False)
        db.query(CoinReservation).filter(CoinReservation.mac == validated.mac).delete()
        db.query(PendingCoin).filter(PendingCoin.mac == validated.mac).delete()
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Failed to finalize coin session for %s: %s", _masked_mac(validated.mac), exc)
        return error("Failed to finalize coin session")

    if coins and client and client.current_ip:
        try:
            from services.firewall_service import FirewallService
            FirewallService().authorize(client.current_ip)
        except Exception as exc:
            logger.error("Coin credit committed but firewall authorization failed for %s: %s", _masked_mac(validated.mac), exc)

    logger.info("Coin session ended for %s", _masked_mac(validated.mac))
    return success({"status": "released"})


@router.post("/close/{mac}")
def close_slot(mac: str, lease_token: str, request: Request, db: Session = Depends(get_db)):
    """Beacon-friendly best-effort close; lease expiry remains authoritative."""
    return release_slot(mac, CoinLeaseRequest(lease_token=lease_token), request, db)


def _is_local_hardware_request(request: Request) -> bool:
    return bool(request.client and request.client.host in ("127.0.0.1", "::1") and not request.headers.get("X-Real-IP"))


@router.get("/hardware-session")
def hardware_session(request: Request, db: Session = Depends(get_db)):
    if not _is_local_hardware_request(request):
        return JSONResponse(status_code=403, content={"success": False, "message": "Local hardware service only."})
    reservation = _active_reservation(db)
    if not reservation or not reservation.lease_id:
        return success({"accepting": False})
    return success({"accepting": True, "lease_id": reservation.lease_id})


@router.get("/hardware-status")
def hardware_status(request: Request, db: Session = Depends(get_db)):
    if not _is_local_hardware_request(request):
        return JSONResponse(status_code=403, content={"success": False, "message": "Local diagnostics only."})
    reservation = _active_reservation(db)
    return success({
        "interface": config.COIN_INTERFACE,
        "relay_on": hardware_service.relay_on,
        "coin_session_active": bool(reservation),
        "lease_remaining_seconds": max(0, int((reservation.expires_at - get_utc_now()).total_seconds())) if reservation else 0,
    })


@router.post("/insert")
def insert_coin(value: int, lease_id: str, request: Request, db: Session = Depends(get_db)):
    if not _is_local_hardware_request(request):
        return JSONResponse(status_code=403, content={"success": False, "message": "Local hardware service only."})
    reservation = _active_reservation(db, lock=True)
    if not reservation or not secrets.compare_digest(reservation.lease_id or "", lease_id):
        logger.warning("Coin rejected because its lease is stale or inactive")
        return JSONResponse(status_code=409, content={"success": False, "message": "No matching active coin session."})
    db.add(PendingCoin(mac=reservation.mac, amount=value, created_at=get_utc_now()))
    db.commit()
    logger.info("Coin value %s accepted for %s", value, _masked_mac(reservation.mac))
    return success({"coin": value, "status": "accumulated"})


if config.DEBUG or config.ENVIRONMENT in ("development", "dev", "test"):
    @router.post("/test/{mac}/{value}")
    def test_coin(mac: str, value: int, body: CoinLeaseRequest, db: Session = Depends(get_db)):
        validated = MacRequest(mac=mac)
        reservation = _active_reservation(db, lock=True)
        if not reservation or reservation.mac != validated.mac or reservation.lease_id != body.lease_token:
            return error("Coin session is not active")
        db.add(PendingCoin(mac=validated.mac, amount=value, created_at=get_utc_now()))
        db.commit()
        return success({"coin": value, "status": "accumulated"})
