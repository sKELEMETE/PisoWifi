from __future__ import annotations

from datetime import timedelta
import logging

import config

logger = logging.getLogger(__name__)


def _gpiod():
    try:
        import gpiod
        from gpiod.line import Direction, Edge, Value
    except ImportError as exc:
        raise RuntimeError("python3-libgpiod (libgpiod v2) is required for GPIO mode") from exc
    return gpiod, Direction, Edge, Value


class GpioPulseCoinInput:
    def __init__(self, on_edge):
        self.on_edge = on_edge
        self.request = None

    def run(self) -> None:
        gpiod, Direction, Edge, _ = _gpiod()
        edge = Edge.RISING if config.GPIO_COIN_EDGE == "rising" else Edge.FALLING
        settings = gpiod.LineSettings(
            direction=Direction.INPUT,
            edge_detection=edge,
            debounce_period=timedelta(milliseconds=config.COIN_DEBOUNCE_MS),
        )
        logger.info(
            "Opening GPIO coin input %s line %s (%s, physical pin %s)",
            config.GPIO_COIN_CHIP,
            config.GPIO_COIN_LINE,
            config.GPIO_COIN_NAME,
            config.GPIO_COIN_PHYSICAL_PIN,
        )
        try:
            request_context = gpiod.request_lines(
                config.GPIO_COIN_CHIP,
                consumer="pisowifi-coin-input",
                config={config.GPIO_COIN_LINE: settings},
            )
        except OSError as exc:
            logger.warning("Kernel GPIO debounce unavailable (%s); using software debounce", exc)
            settings = gpiod.LineSettings(direction=Direction.INPUT, edge_detection=edge)
            request_context = gpiod.request_lines(
                config.GPIO_COIN_CHIP,
                consumer="pisowifi-coin-input",
                config={config.GPIO_COIN_LINE: settings},
            )
        with request_context as request:
            self.request = request
            while True:
                if not request.wait_edge_events(timedelta(seconds=1)):
                    continue
                for _event in request.read_edge_events():
                    self.on_edge()


class GpioRelayPowerController:
    def __init__(self):
        self.request = None
        self.is_on = False

    def start(self) -> None:
        gpiod, Direction, _, Value = _gpiod()
        inactive = Value.ACTIVE if config.GPIO_RELAY_ACTIVE_LOW else Value.INACTIVE
        settings = gpiod.LineSettings(direction=Direction.OUTPUT, output_value=inactive)
        self.request = gpiod.request_lines(
            config.GPIO_RELAY_CHIP,
            consumer="pisowifi-coin-relay",
            config={config.GPIO_RELAY_LINE: settings},
        )
        self.is_on = False
        logger.info("Coin selector relay initialized OFF")

    def set_enabled(self, enabled: bool) -> None:
        if self.request is None:
            self.start()
        _, _, _, Value = _gpiod()
        electrical_active = not enabled if config.GPIO_RELAY_ACTIVE_LOW else enabled
        value = Value.ACTIVE if electrical_active else Value.INACTIVE
        self.request.set_value(config.GPIO_RELAY_LINE, value)
        self.is_on = enabled
        logger.info("Coin selector relay %s", "ON" if enabled else "OFF")

    def close(self) -> None:
        try:
            if self.request is not None:
                self.set_enabled(False)
        finally:
            if self.request is not None:
                self.request.release()
                self.request = None


class NoOpPowerController:
    """Arduino installations retain their existing external power behavior."""

    is_on = False

    def start(self) -> None:
        return None

    def set_enabled(self, enabled: bool) -> None:
        self.is_on = False

    def close(self) -> None:
        self.is_on = False
