from __future__ import annotations

import logging
import threading

import config
from coin_hardware.gpio import GpioRelayPowerController, NoOpPowerController

logger = logging.getLogger(__name__)


class HardwareService:
    def __init__(self, controller=None):
        self.controller = controller or self._configured_controller()
        self._lock = threading.Lock()
        self.started = False

    @staticmethod
    def _configured_controller():
        if config.COIN_INTERFACE == "gpio":
            return GpioRelayPowerController()
        return NoOpPowerController()

    def start(self) -> None:
        with self._lock:
            if not self.started:
                self.controller.start()
                self.started = True

    def set_accepting(self, accepting: bool) -> None:
        with self._lock:
            if not self.started:
                self.controller.start()
                self.started = True
            self.controller.set_enabled(accepting)

    def shutdown(self) -> None:
        with self._lock:
            self.controller.close()
            self.started = False

    @property
    def relay_on(self) -> bool:
        return bool(self.controller.is_on)


hardware_service = HardwareService()
