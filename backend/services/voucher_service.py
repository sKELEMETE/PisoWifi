from repositories.voucher_repository import VoucherRepository


class VoucherService:

    def __init__(self, repository: VoucherRepository):
        self.repository = repository

    def validate(self, code: str):
        return self.repository.get_by_code(code)
