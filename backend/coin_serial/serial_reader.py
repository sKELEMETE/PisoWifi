import serial
import config
import time

class SerialReader:
    def __init__(self):
        self.serial = serial.Serial(
            port=config.SERIAL_PORT,
            baudrate=config.SERIAL_BAUDRATE,
            timeout=config.SERIAL_TIMEOUT,
        )

    def read_line(self) -> str | None:
        if not self.serial.is_open:
            return None

        line = self.serial.readline()

        if not line:
            return None

        return line.decode(errors="ignore").strip()


class MockSerialReader:
    def __init__(self):
        self.is_open = True

    def read_line(self) -> str | None:
        # Prevent 100% CPU lockup by sleeping, mimicking serial timeout
        time.sleep(config.SERIAL_TIMEOUT)
        return None
