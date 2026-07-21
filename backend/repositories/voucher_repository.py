from sqlalchemy import select, func, update
from sqlalchemy.orm import joinedload

from models.voucher import Voucher, VoucherStatus
from repositories.base_repository import BaseRepository


class VoucherRepository(BaseRepository):

    def get_by_code(self, code: str, for_update: bool = False):
        stmt = select(Voucher).where(Voucher.code == code)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def redeem_atomic(self, code: str, client_id: int, now) -> int:
        stmt = (
            update(Voucher)
            .where(Voucher.code == code)
            .where(Voucher.status == VoucherStatus.UNUSED)
            .where(
                (Voucher.expires_at.is_(None)) | (Voucher.expires_at > now)
            )
            .values(
                status=VoucherStatus.USED,
                used_at=now,
                used_by_client_id=client_id,
            )
        )
        result = self.db.execute(stmt)
        return result.rowcount

    def get_by_id(self, voucher_id: int):
        return self.db.get(Voucher, voucher_id)

    def get_all(
        self,
        status_filter: VoucherStatus | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
    ):
        stmt = select(Voucher).options(joinedload(Voucher.used_by_client))
        
        if status_filter:
            stmt = stmt.where(Voucher.status == status_filter)
        
        order_col = getattr(Voucher, order_by, Voucher.created_at)
        if order_desc:
            stmt = stmt.order_by(order_col.desc())
        else:
            stmt = stmt.order_by(order_col.asc())
        
        stmt = stmt.limit(limit).offset(offset)
        return self.db.execute(stmt).scalars().all()

    def count_all(self, status_filter: VoucherStatus | None = None) -> int:
        stmt = select(func.count()).select_from(Voucher)
        if status_filter:
            stmt = stmt.where(Voucher.status == status_filter)
        return self.db.execute(stmt).scalar_one()

    def delete(self, voucher: Voucher):
        self.db.delete(voucher)
        self.db.commit()

    def update(self, voucher: Voucher):
        self.db.commit()
        self.db.refresh(voucher)
        return voucher
