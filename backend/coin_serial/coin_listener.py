import logging
import time
import httpx

import config
from coin_serial.debounce import Debouncer
from coin_serial.packet_validator import validate_packet
from coin_serial.serial_manager import SerialManager

logger = logging.getLogger(__name__)


class CoinListener:

    def __init__(self):
        self.manager = SerialManager()
        self.debouncer = Debouncer(delay_ms=config.SERIAL_DEBOUNCE_MS)

    def process_coin_via_api(self, value: int) -> bool:
        """
        Sends a POST request to the local API backend to record the coin pulse.
        Returns True if the coin was successfully accumulated under an active reservation.
        """
        url = f"http://127.0.0.1:{config.BACKEND_PORT}/api/v1/coin/insert"
        try:
            res = httpx.post(url, params={"value": value}, timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                if data.get("success"):
                    mac = data.get("data", {}).get("mac", "unknown")
                    logger.info("Successfully recorded %d PHP coin via API for client %s.", value, mac)
                    return True
                else:
                    logger.warning("Coin rejected by API: %s", data.get("message"))
            else:
                logger.error("API returned error status %d: %s", res.status_code, res.text)
        except Exception as exc:
            logger.error("Failed to connect to local API to process coin: %s", exc)
        return False

    def run(self):
        self.manager.connect()

        logger.info("Listening for coin acceptor pulses...")
        while True:
            packet = self.manager.read()
            if packet is None:
                continue

            value = validate_packet(packet)
            if value is None:
                continue

            # Debounce
            if not self.debouncer.debounce(value):
                continue

            logger.info("Coin pulse received: %d PHP", value)
            self.process_coin_via_api(value)