from serial.tools import list_ports


def detect_serial_device() -> str | None:
    """
    Detect the first USB serial device.
    """

    ports = list_ports.comports()

    for port in ports:
        if "USB" in port.description.upper():
            return port.device

    return None
