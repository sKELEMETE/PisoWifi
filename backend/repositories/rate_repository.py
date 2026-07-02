from sqlalchemy import select

from models.rate import Rate
from repositories.base_repository import BaseRepository


class RateRepository(BaseRepository):

    def get_by_coin(self, coin_value: int):
        stmt = (
            select(Rate)
            .where(Rate.coin_value == coin_value)
            .where(Rate.enabled.is_(True))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_enabled(self):
        stmt = (
            select(Rate)
            .where(Rate.enabled.is_(True))
            .order_by(Rate.coin_value)
        )
        return self.db.execute(stmt).scalars().all()
