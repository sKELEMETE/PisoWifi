from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.v1 import coin as coin_api
from coin_hardware.gpio import GpioRelayPowerController
from coin_hardware.pulse import PulseBurstGrouper, map_pulse_count
from coin_serial.packet_validator import validate_packet
from database import Base
from models.client import Client
from models.coin_reservation import CoinReservation, PendingCoin
from schemas.validation import CoinLeaseRequest
from scheduler.jobs import check_expired_reservations
from services.hardware_service import HardwareService, hardware_service
from utils.time_utils import get_utc_now


class FakePower:
    def __init__(self, fail_on_enable=False):
        self.is_on = False
        self.fail_on_enable = fail_on_enable

    def start(self):
        self.is_on = False

    def set_enabled(self, enabled):
        if enabled and self.fail_on_enable:
            raise OSError("GPIO unavailable")
        self.is_on = enabled

    def close(self):
        self.is_on = False


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def fake_power():
    original = hardware_service.controller
    original_started = hardware_service.started
    controller = FakePower()
    hardware_service.controller = controller
    hardware_service.started = False
    yield controller
    hardware_service.controller = original
    hardware_service.started = original_started


def client_request(ip):
    return SimpleNamespace(headers={"X-Real-IP": ip}, client=SimpleNamespace(host="127.0.0.1"))


def hardware_request():
    return SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))


def add_client(db, mac, ip):
    db.add(Client(mac_address=mac, current_ip=ip))
    db.commit()


def activate(db, mac="AA:BB:CC:DD:EE:01", ip="10.0.0.2"):
    add_client(db, mac, ip)
    result = coin_api.activate_slot(mac, client_request(ip), db)
    return result.data["lease_token"]


def test_arduino_pulse_protocol_remains_compatible():
    assert validate_packet("PULSE: 1") == 1
    assert validate_packet("PULSE: 5") == 5
    assert validate_packet("PULSES: 10") == 10
    assert validate_packet("COIN: 1") is None


def test_arduino_backend_does_not_require_gpio(monkeypatch):
    import services.hardware_service as hardware_module
    from coin_hardware.gpio import NoOpPowerController

    monkeypatch.setattr(hardware_module.config, "COIN_INTERFACE", "arduino")
    service = HardwareService()
    assert isinstance(service.controller, NoOpPowerController)
    service.start()
    service.set_accepting(True)
    assert not service.relay_on


def test_gpio_single_and_multiple_pulse_bursts_and_debounce():
    bursts = []
    grouper = PulseBurstGrouper(lambda count, context: bursts.append((count, context)), 20, 250, lambda: "lease")
    assert grouper.add_edge(1.0)
    assert not grouper.add_edge(1.01)
    assert grouper.flush() == 1
    assert bursts == [(1, "lease")]

    assert grouper.add_edge(2.0)
    assert grouper.add_edge(2.03)
    assert grouper.add_edge(2.06)
    assert grouper.flush() == 3
    assert bursts[-1] == (3, "lease")
    grouper.close()


def test_pulse_mapping_unknown_is_safe():
    mapping = {1: 1, 5: 5}
    assert map_pulse_count(5, mapping) == 5
    assert map_pulse_count(4, mapping) is None


def test_coin_rejected_without_active_session(db):
    response = coin_api.insert_coin(5, "stale-token", hardware_request(), db)
    assert response.status_code == 409
    assert db.query(PendingCoin).count() == 0


def test_active_owner_gets_pending_credit_and_second_customer_is_blocked(db):
    token = activate(db)
    response = coin_api.insert_coin(5, token, hardware_request(), db)
    assert response.success
    pending = db.query(PendingCoin).one()
    assert pending.mac == "AA:BB:CC:DD:EE:01"
    assert pending.amount == 5

    add_client(db, "AA:BB:CC:DD:EE:02", "10.0.0.3")
    busy = coin_api.activate_slot("AA:BB:CC:DD:EE:02", client_request("10.0.0.3"), db)
    assert busy.status_code == 409


def test_relay_on_start_off_release_and_credit_owner(db, fake_power, monkeypatch):
    from services.firewall_service import FirewallService

    monkeypatch.setattr(FirewallService, "authorize", lambda self, ip: None)
    token = activate(db)
    assert fake_power.is_on
    coin_api.insert_coin(1, token, hardware_request(), db)
    credited = []

    class FakeCoinService:
        def process_coins_bulk(self, mac, coins, **_kwargs):
            credited.append((mac, coins))

    monkeypatch.setattr(coin_api, "_coin_service", lambda _db: FakeCoinService())
    result = coin_api.release_slot(
        "AA:BB:CC:DD:EE:01",
        CoinLeaseRequest(lease_token=token),
        client_request("10.0.0.2"),
        db,
    )
    assert result.success
    assert credited == [("AA:BB:CC:DD:EE:01", [1])]
    assert not fake_power.is_on


def test_lease_expiry_turns_relay_off(db, fake_power):
    token = activate(db)
    assert token and fake_power.is_on
    reservation = db.query(CoinReservation).one()
    reservation.expires_at = get_utc_now() - timedelta(seconds=1)
    db.commit()
    check_expired_reservations(db)
    assert not fake_power.is_on
    assert db.query(CoinReservation).count() == 0


def test_stale_heartbeat_and_coin_cannot_cross_ownership(db):
    old_token = activate(db)
    old = db.query(CoinReservation).one()
    old.expires_at = get_utc_now() - timedelta(seconds=1)
    db.commit()
    check_expired_reservations(db)

    add_client(db, "AA:BB:CC:DD:EE:02", "10.0.0.3")
    new_result = coin_api.activate_slot("AA:BB:CC:DD:EE:02", client_request("10.0.0.3"), db)
    new_token = new_result.data["lease_token"]
    assert new_token != old_token

    stale_heartbeat = coin_api.heartbeat_slot(
        "AA:BB:CC:DD:EE:01",
        CoinLeaseRequest(lease_token=old_token),
        client_request("10.0.0.2"),
        db,
    )
    assert stale_heartbeat.status_code == 409
    stale_coin = coin_api.insert_coin(5, old_token, hardware_request(), db)
    assert stale_coin.status_code == 409
    assert db.query(PendingCoin).count() == 0


def test_gpio_failure_does_not_leave_reservation_or_relay_on(db):
    add_client(db, "AA:BB:CC:DD:EE:01", "10.0.0.2")
    hardware_service.controller = FakePower(fail_on_enable=True)
    hardware_service.started = False
    response = coin_api.activate_slot("AA:BB:CC:DD:EE:01", client_request("10.0.0.2"), db)
    assert response.status_code == 503
    assert db.query(CoinReservation).count() == 0
    assert not hardware_service.relay_on


class FakeValue:
    ACTIVE = "active"
    INACTIVE = "inactive"


class FakeDirection:
    OUTPUT = "output"


class FakeRequest:
    def __init__(self):
        self.values = []
        self.released = False

    def set_value(self, _offset, value):
        self.values.append(value)

    def release(self):
        self.released = True


class FakeGpiod:
    def __init__(self):
        self.request = FakeRequest()
        self.initial = None

    def LineSettings(self, **kwargs):
        self.initial = kwargs["output_value"]
        return kwargs

    def request_lines(self, *_args, **_kwargs):
        return self.request


@pytest.mark.parametrize(
    "active_low,initial,on,off",
    [
        (True, FakeValue.ACTIVE, FakeValue.INACTIVE, FakeValue.ACTIVE),
        (False, FakeValue.INACTIVE, FakeValue.ACTIVE, FakeValue.INACTIVE),
    ],
)
def test_relay_active_low_and_high(monkeypatch, active_low, initial, on, off):
    import coin_hardware.gpio as gpio_module

    fake = FakeGpiod()
    monkeypatch.setattr(gpio_module, "_gpiod", lambda: (fake, FakeDirection, None, FakeValue))
    monkeypatch.setattr(gpio_module.config, "GPIO_RELAY_ACTIVE_LOW", active_low)
    monkeypatch.setattr(gpio_module.config, "GPIO_RELAY_CHIP", "/dev/gpiochip0")
    monkeypatch.setattr(gpio_module.config, "GPIO_RELAY_LINE", 9)
    relay = GpioRelayPowerController()
    relay.start()
    relay.set_enabled(True)
    relay.set_enabled(False)
    relay.close()
    assert fake.initial == initial
    assert fake.request.values[:2] == [on, off]
    assert fake.request.values[-1] == off
