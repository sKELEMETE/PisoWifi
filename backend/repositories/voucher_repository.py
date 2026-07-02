from sqlalchemy import select

from models.voucher import Voucher
from repositories.base_repository import BaseRepository


class VoucherRepository(BaseRepository):

    def get_by_code(self, code: str):
        stmt = select(Voucher).where(Voucher.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def update(self, voucher: Voucher):
        self.db.commit()
        self.db.refresh(voucher)
        return voucher
