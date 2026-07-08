from services.client_service import ClientService
from services.session_service import SessionService
from services.coin_service import CoinService
from services.voucher_service import VoucherService
from services.firewall_service import FirewallService
from services.network_service import NetworkService
from services.health_service import HealthService
from services.backup_service import BackupService


def test_service_imports():
    assert ClientService is not None
    assert SessionService is not None
    assert CoinService is not None
    assert VoucherService is not None
    assert FirewallService is not None
    assert NetworkService is not None
    assert HealthService is not None
    assert BackupService is not None
