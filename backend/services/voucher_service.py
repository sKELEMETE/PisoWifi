from repositories.voucher_repository import VoucherRepository
from services.voucher_generator import VoucherGenerator, VoucherCreationService
from models.voucher import Voucher, VoucherStatus
import logging

logger = logging.getLogger(__name__)


class VoucherService:

    def __init__(self, repository: VoucherRepository):
        self.repository = repository
        self.generator = VoucherGenerator()
        self.creation_service = VoucherCreationService(repository.db, self.generator)

    def validate(self, code: str):
        return self.repository.get_by_code(code)

    def create_voucher(
        self,
        minutes: int,
        expires_at=None,
        created_by=None,
        notes: str | None = None,
    ) -> Voucher:
        """Create a single voucher."""
        return self.creation_service.create_voucher(
            minutes=minutes,
            expires_at=expires_at,
            created_by=created_by,
            notes=notes,
        )

    def create_vouchers_bulk(
        self,
        count: int,
        minutes: int,
        expires_at=None,
        created_by=None,
        notes: str | None = None,
    ) -> list[Voucher]:
        """Create multiple vouchers in bulk."""
        return self.creation_service.create_vouchers_bulk(
            count=count,
            minutes=minutes,
            expires_at=expires_at,
            created_by=created_by,
            notes=notes,
        )

    def get_voucher(self, voucher_id: int) -> Voucher | None:
        return self.repository.get_by_id(voucher_id)

    def list_vouchers(
        self,
        status_filter: VoucherStatus | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Voucher]:
        return self.repository.get_all(
            status_filter=status_filter,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
        )

    def count_vouchers(self, status_filter: VoucherStatus | None = None) -> int:
        return self.repository.count_all(status_filter=status_filter)

    def delete_voucher(self, voucher_id: int) -> bool:
        voucher = self.repository.get_by_id(voucher_id)
        if not voucher:
            return False
        self.repository.delete(voucher)
        logger.info("Voucher deleted: id=%d", voucher_id)
        return True
