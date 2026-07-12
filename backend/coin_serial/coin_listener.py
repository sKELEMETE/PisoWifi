import logging

from database import SessionLocal

from coin_serial.debounce import Debouncer
from coin_serial.packet_validator import validate_packet
from coin_serial.serial_manager import SerialManager

from repositories.rate_repository import RateRepository
from repositories.client_repository import ClientRepository
from repositories.sales_repository import SalesRepository
from repositories.session_repository import SessionRepository

from services.session_service import SessionService
from services.coin_service import CoinService

logger = logging.getLogger(__name__)


class CoinListener:

    def __init__(self):
        self.manager = SerialManager()
        self.debounce = Debouncer()

    def get_active_mac(self):
        try:
            with open("/tmp/active_mac.txt", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def update_pending_balance(self, value):
        current = 0

        try:
            with open("/tmp/pending_coin.txt", "r") as f:
                current = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            pass

        with open("/tmp/pending_coin.txt", "w") as f:
            f.write(str(current + value))

    def process_coin(self, mac, value):

        db = SessionLocal()

        try:

            rate_repository = RateRepository(db)
            client_repository = ClientRepository(db)
            sales_repository = SalesRepository(db)
            session_repository = SessionRepository(db)

            session_service = SessionService(session_repository)

            coin_service = CoinService(
                rate_repository,
                client_repository,
                session_service,
                sales_repository,
            )

            self.update_pending_balance(value)

            coin_service.process_coin(mac, value)

        finally:
            db.close()

    def run(self):

        self.manager.connect()

        logger.info("Coin listener started.")

        while True:

            packet = self.manager.read()

            if packet is None:
                continue

            if not self.debounce.allow(packet):
                continue

            value = validate_packet(packet)

            if value is None:
                logger.warning("Invalid packet: %s", packet)
                continue

            logger.info("Coin detected: ₱%s", value)

            mac = self.get_active_mac()

            if mac:
                self.process_coin(mac, value)
            else:
                logger.warning("Coin inserted. No active client MAC found.")

    def is_connected(self):
        return self.manager.is_connected()
