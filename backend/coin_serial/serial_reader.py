import serial

import config

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
