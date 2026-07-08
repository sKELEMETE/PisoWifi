from repositories.client_repository import ClientRepository
from repositories.session_repository import SessionRepository
from repositories.rate_repository import RateRepository
from repositories.voucher_repository import VoucherRepository
from repositories.sales_repository import SalesRepository


def test_repository_imports():
    assert ClientRepository is not None
    assert SessionRepository is not None
    assert RateRepository is not None
    assert VoucherRepository is not None
    assert SalesRepository is not None
