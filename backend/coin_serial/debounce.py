import time

import config

class Debouncer:
    def __init__(self):
        self.last_packet = None
        self.last_time = 0

    def allow(self, packet: str) -> bool:
        now = time.monotonic()

        if (
            packet == self.last_packet
            and (now - self.last_time) * 1000 < config.SERIAL_DEBOUNCE_MS
        ):
            return False

        self.last_packet = packet
        self.last_time = now

        return True
