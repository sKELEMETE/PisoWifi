import logging
import time
import httpx

import config
from coin_serial.debounce import Debouncer
from coin_serial.packet_validator import validate_packet
from coin_serial.serial_manager import SerialManager
from coin_serial.coin_spool import CoinSpool

logger = logging.getLogger(__name__)


class CoinListener:

    def __init__(self):
        self.manager = SerialManager()
        self.debouncer = Debouncer()
        self.spool = CoinSpool()

    def get_active_lease(self) -> str | None:
        url = f"http://127.0.0.1:{config.BACKEND_PORT}/api/v1/coin/hardware-session"
        try:
            response = httpx.get(url, timeout=2.0)
            data = response.json().get("data", {}) if response.status_code == 200 else {}
            return data.get("lease_id") if data.get("accepting") else None
        except Exception as exc:
            logger.error("Failed to query active coin lease: %s", exc)
            return None

    def process_coin_via_api(
        self,
        value: int,
        lease_id: str | None = None,
        source: str = "serial",
        pulse_count: int | None = None
    ) -> bool:
        """
        Durably spools the event and dispatches it to the local API backend with ACK/retry.
        Returns True if the coin was successfully accepted and acknowledged.
        """
        lease_id = lease_id or self.get_active_lease()
        if not lease_id:
            logger.warning("Coin ignored because no active customer lease exists")
            return False

        # Durably record event to write-ahead spool before network dispatch
        event = self.spool.create_event(
            denomination=value,
            lease_id=lease_id,
            source=source,
            pulse_count=pulse_count,
        )

        return self.spool.dispatch_with_retry(event)

    def run(self):
        logger.info("Reconciling unacknowledged coin events from write-ahead spool...")
        self.spool.reconcile_spool()

        logger.info("Initializing serial manager connection...")
        self.manager.connect()

        logger.info("Listening for coin acceptor pulses...")
        while True:
            packet = self.manager.read()
            if packet is None:
                continue

            logger.info("Raw packet received: %r", packet)

            # Debounce raw serial line
            if not self.debouncer.allow(packet):
                logger.warning("Packet debounced (ignored): %r", packet)
                continue

            value = validate_packet(packet)
            if value is None:
                logger.warning("Packet validation failed for input: %r", packet)
                continue

            logger.info("Packet validated successfully. Extracted value: %d", value)
            logger.info("Coin pulse allowed. Dispatched value: %d", value)

            success = self.process_coin_via_api(value)
            logger.info("REST API post status: %s", "Success" if success else "Failed")


class GpioCoinListener(CoinListener):
    def __init__(self):
        from coin_hardware.gpio import GpioPulseCoinInput
        from coin_hardware.pulse import PulseBurstGrouper

        self.manager = None
        self.debouncer = None
        self.grouper = PulseBurstGrouper(
            callback=self._process_burst,
            debounce_ms=config.COIN_DEBOUNCE_MS,
            inter_pulse_gap_ms=config.COIN_INTER_PULSE_GAP_MS,
            context_factory=self.get_active_lease,
        )
        self.input = GpioPulseCoinInput(self.grouper.add_edge)

    def _process_burst(self, pulse_count: int, lease_id: object | None) -> None:
        from coin_hardware.pulse import map_pulse_count

        logger.info("GPIO coin burst detected: %d pulse(s)", pulse_count)
        if not lease_id:
            logger.warning("GPIO pulse burst ignored because no lease was active at its first edge")
            return
        value = map_pulse_count(pulse_count, config.COIN_PULSE_MAP)
        if value is None:
            logger.warning("Unknown GPIO pulse count %d ignored", pulse_count)
            return
        self.process_coin_via_api(value, str(lease_id))

    def run(self):
        logger.info("Listening for coin pulses using native libgpiod input")
        self.input.run()
