import logging
import os

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

    def run(self):
        self.manager.connect()
        logger.info("Coin listener started.")

        while True:
            packet = self.manager.read()
            print(f"RAW: {packet}")
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

            print("ACTIVE MAC =", repr(mac))

            if mac:
                print("PROCESSING", value, "FOR", mac)
            else:
                print("NO ACTIVE MAC")

            if mac:
                self.update_pending_balance(value)
                self.coin_service.process_coin(mac, value)
            else:
                logger.warning("Coin inserted. No active client MAC found.")

    def is_connected(self):
        return self.manager.is_connected()
