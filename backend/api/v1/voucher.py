from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from repositories.rate_repository import RateRepository
from database import get_db
from repositories.voucher_repository import VoucherRepository
from repositories.client_repository import ClientRepository
from repositories.session_repository import SessionRepository

from services.session_service import SessionService

from schemas.validation import MacRequest, VoucherRequest
from utils.api_response import success, error

router = APIRouter(prefix="/api/v1/voucher", tags=["Voucher"])

@router.post("/redeem/{code}/{mac}")
def redeem_voucher(code: str, mac: str, db: Session = Depends(get_db)):
    validated_mac = MacRequest(mac=mac)
    validated_code = VoucherRequest(code=code)

    voucher_repo = VoucherRepository(db)
    client_repo = ClientRepository(db)
    session_repo = SessionRepository(db)
    session_service = SessionService(session_repo)

    client = client_repo.get_by_mac(validated_mac.mac)
    if not client:
        return error("Client not found")

    voucher = voucher_repo.get_by_code(validated_code.code)
    if not voucher:
        return error("Invalid voucher")

    if voucher.status == "USED":
        return error("Voucher already used")

    if voucher.status == "EXPIRED":
        return error("Voucher expired")

    rate_repo = RateRepository(db)
    rate = rate_repo.get_by_coin(0)
    rate_id = rate.id if rate else None

    session = session_service.create_or_extend_session(
        client_id=client.id,
        rate_id=rate_id,
        minutes=voucher.minutes,
    )

    voucher.status = "USED"
    db.commit()

    return success({
        "session_id": session.id,
        "status": session.status,
        "added_minutes": voucher.minutes
    })
