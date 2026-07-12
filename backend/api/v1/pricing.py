from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from repositories.rate_repository import RateRepository
from utils.api_response import success

router = APIRouter(
    prefix="/pricing",
    tags=["Pricing"],
)


@router.get("")
def get_pricing(db: Session = Depends(get_db)):
    repository = RateRepository(db)

    rates = repository.get_all_enabled()

    data = [
        {
            "id": rate.id,
            "amount": rate.coin_value,
            "minutes": rate.minutes,
        }
        for rate in rates
    ]

    return success(
        message="Pricing retrieved.",
        data=data,
    )
