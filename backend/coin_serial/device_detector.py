import os
import config
from serial.tools import list_ports


def detect_serial_device() -> str | None:
    """
    Detect the serial device.
    If config.SERIAL_PORT is specified and not 'AUTO', return it directly.
    Otherwise, search comports for USB adapters, then ACM, then hardware UARTs.
    """
    # 1. Manual override takes precedence
    if config.SERIAL_PORT and config.SERIAL_PORT.upper() != "AUTO":
        if os.path.exists(config.SERIAL_PORT) or config.SERIAL_PORT.startswith("COM"):
            return config.SERIAL_PORT
        # If it doesn't exist on disk, we still return it as configured
        return config.SERIAL_PORT

    # 2. Dynamic auto-detection
    ports = list_ports.comports()

    # Priority 1: USB serial adapters (e.g. CH340, CP210x, Arduino Uno/Nano)
    for port in ports:
        desc = port.description.upper()
        if "USB" in desc or "ACM" in desc or "ARDUINO" in desc:
            return port.device

    # Priority 2: Common hardware serial ports on Linux SBCs (Raspberry Pi/Orange Pi)
    # Search for AMA or S ports that exist and are active
    common_sbc_paths = [
        "/dev/ttyAMA0", "/dev/ttyAMA1",
        "/dev/ttyS0", "/dev/ttyS1", "/dev/ttyS2", "/dev/ttyS3",
        "/dev/ttyO0", "/dev/ttyO1", "/dev/ttyO2", "/dev/ttyO3"
    ]
    for path in common_sbc_paths:
        if os.path.exists(path):
            # Check if this port is in list_ports to verify it's registered
            for port in ports:
                if port.device == path:
                    return path
            # Fallback: if it exists on disk, we can assume it's valid
            return path

    # Priority 3: Any port in ports list (fallback)
    if ports:
        return ports[0].device

    return None
