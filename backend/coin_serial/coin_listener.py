import logging

from coin_serial.debounce import Debouncer
from coin_serial.packet_validator import validate_packet
from coin_serial.serial_manager import SerialManager
from services.coin_service import CoinService

logger = logging.getLogger(__name__)


class CoinListener:
    def __init__(self, coin_service: CoinService):
        self.manager = SerialManager()
        self.debounce = Debouncer()
        self.coin_service = coin_service

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

            self.coin_service.process_coin(
                "AA:BB:CC:DD:EE:FF",
                value,
            )

    def is_connected(self):
        return self.manager.is_connected()
