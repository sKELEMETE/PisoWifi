from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging

from database import get_db
from models.voucher import Voucher, VoucherStatus
from models.sale import Sale, PaymentMethod
from repositories.rate_repository import RateRepository
from repositories.voucher_repository import VoucherRepository
from repositories.client_repository import ClientRepository
from repositories.session_repository import SessionRepository
from services.session_service import SessionService
from services.network_service import NetworkService
from schemas.validation import MacRequest, VoucherRequest
from utils.api_response import success, error
from utils.rate_limiter import voucher_limiter
from utils.time_utils import get_utc_now

router = APIRouter(prefix="/api/v1/voucher", tags=["Voucher"])

logger = logging.getLogger(__name__)


class RedeemVoucherRequest(BaseModel):
    code: str
    mac: str


def _process_voucher_redemption(code: str, mac: str, client_ip: str, db: Session):
    validated_mac = MacRequest(mac=mac)
    validated_code = VoucherRequest(code=code)

    # Rate limiting by combined (IP, MAC) key as well as MAC alone to prevent spoofing
    limiter_key = f"{client_ip}:{validated_mac.mac}"
    locked_mac, remaining_mac = voucher_limiter.is_locked(validated_mac.mac)
    locked_key, remaining_key = voucher_limiter.is_locked(limiter_key)

    if locked_mac or locked_key:
        remaining = max(remaining_mac, remaining_key)
        logger.warning("Voucher redemption rate limited: IP %s / MAC %s locked for %d seconds", client_ip, validated_mac.mac, remaining)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many voucher redemption attempts. Try again in {remaining} seconds."
        )

    client_repo = ClientRepository(db)
    voucher_repo = VoucherRepository(db)
    session_repo = SessionRepository(db)
    session_service = SessionService(session_repo)

    client = client_repo.get_or_create(validated_mac.mac)

    # Associate client IP if missing or changed
    if client_ip and client_ip != "127.0.0.1":
        client.current_ip = client_ip

    now = get_utc_now()

    # Atomic redemption: try to claim the voucher with a single UPDATE
    # This prevents double-redemption race conditions
    rows = voucher_repo.redeem_atomic(validated_code.code, client.id, now)
    if rows == 0:
        # Could not claim - check why for a helpful error message
        voucher = voucher_repo.get_by_code(validated_code.code)
        if not voucher:
            logger.warning("Voucher redemption failed: invalid voucher code %s", validated_code.code)
            voucher_limiter.record_attempt(validated_mac.mac, success=False)
            voucher_limiter.record_attempt(limiter_key, success=False)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid voucher")

        logger.warning("Voucher redemption failed: voucher %s status is %s", validated_code.code, voucher.status)
        voucher_limiter.record_attempt(validated_mac.mac, success=False)
        voucher_limiter.record_attempt(limiter_key, success=False)

        if voucher.expires_at and voucher.expires_at < now:
            if voucher.status == VoucherStatus.UNUSED:
                voucher.status = VoucherStatus.EXPIRED
                db.commit()
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Voucher expired")

        if voucher.status == VoucherStatus.USED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Voucher already used")
        if voucher.status == VoucherStatus.EXPIRED:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Voucher expired")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Voucher not available")

    # Fetch the updated voucher to get metadata (minutes, etc.)
    voucher = voucher_repo.get_by_code(validated_code.code)

    rate_repo = RateRepository(db)
    rate = rate_repo.get_by_coin(0)
    rate_id = rate.id if rate else None

    if not rate_id:
        from models.rate import Rate as RateModel
        first_rate = db.query(RateModel).filter(RateModel.enabled.is_(True)).first()
        rate_id = first_rate.id if first_rate else None

    if not rate_id:
        logger.error("Voucher redemption failed: no rates configured in database")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Pricing system misconfigured")

    session = session_service.create_or_extend_session(
        client_id=client.id,
        rate_id=rate_id,
        minutes=voucher.minutes,
        authorize=False,
        commit=False,
    )
    db.flush()

    # Record sales entry for reporting
    sale = Sale(
        session_id=session.id,
        rate_id=rate_id,
        amount=0,
        minutes=voucher.minutes,
        payment_method=PaymentMethod.VOUCHER,
        created_at=now,
    )
    db.add(sale)

    # Atomic firewall authorization check
    if client.current_ip:
        try:
            session_service.firewall.authorize(client.current_ip)
        except Exception as exc:
            db.rollback()
            logger.error("Firewall authorization failed during voucher redemption for IP %s: %s", client.current_ip, exc)
            voucher_limiter.record_attempt(validated_mac.mac, success=False)
            voucher_limiter.record_attempt(limiter_key, success=False)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Network authorization failed. Please try redeeming again."
            )

    # Commit DB transaction after firewall authorization succeeds
    db.commit()

    # Reset rate limiters on success
    voucher_limiter.record_attempt(validated_mac.mac, success=True)
    voucher_limiter.record_attempt(limiter_key, success=True)

    logger.info("Voucher %s redeemed successfully by client %s (MAC: %s), session %s created with %d minutes",
                validated_code.code, client.id, validated_mac.mac, session.id, voucher.minutes)

    return success({
        "session_id": session.id,
        "status": session.status,
        "added_minutes": voucher.minutes
    })


@router.post("/redeem")
def redeem_voucher_body(
    payload: RedeemVoucherRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Secure voucher redemption endpoint using JSON request body."""
    client_ip = NetworkService().get_client_ip(request)
    return _process_voucher_redemption(payload.code, payload.mac, client_ip, db)


@router.post("/redeem/{code}/{mac}", deprecated=True)
def redeem_voucher(
    code: str,
    mac: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Legacy redemption route. Deprecated: prefer POST /api/v1/voucher/redeem with JSON body."""
    client_ip = NetworkService().get_client_ip(request)
    return _process_voucher_redemption(code, mac, client_ip, db)

