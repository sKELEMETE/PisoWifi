import os
import serial
import time
import config
from serial.tools import list_ports

# Target USB VID:PID pairs for common Arduino / USB-to-Serial chips
TARGET_VID_PIDS = {
    (0x0403, 0x6001),  # FTDI FT232R
    (0x1A86, 0x7523),  # QinHeng CH340
    (0x10C4, 0xEA60),  # CP210x
    (0x2341, 0x0043),  # Arduino Uno
    (0x2341, 0x0001),  # Arduino Uno/Mega
    (0x067B, 0x2303),  # Prolific PL2303
}


def detect_serial_device() -> str | None:
    """
    Detect the serial device.
    If config.SERIAL_PORT is specified and not 'AUTO', return it directly.
    Otherwise, dynamically scan and prioritize serial ports by Arduino compatibility score,
    probing candidate ports for active PisoWiFi coin selector handshake signatures.
    """
    # 1. Manual override takes precedence
    if config.SERIAL_PORT and config.SERIAL_PORT.upper() != "AUTO":
        return config.SERIAL_PORT

    # 2. Dynamic auto-detection
    ports = list_ports.comports()
    candidates = []

    for port in ports:
        score = 0
        desc = port.description.upper()

        # Score based on VID:PID
        if port.vid is not None and port.pid is not None:
            if (port.vid, port.pid) in TARGET_VID_PIDS:
                score += 100

        # Score based on description
        if "USB" in desc or "ACM" in desc or "ARDUINO" in desc:
            score += 50

        # Include all USB/ACM and hardware SBC serial paths
        is_candidate = score >= 50 or any(
            x in port.device for x in ["ttyAMA", "ttyS", "ttyO", "ttyUSB"]
        )

        if is_candidate:
            candidates.append((score, port.device))

    # Sort candidates: highest score first, then descending alphabetically by device path (e.g. ttyUSB1 before ttyUSB0)
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    if not candidates:
        return None

    # Probe candidates to identify the active PisoWiFi Arduino selector
    for score, device in candidates:
        if score < 50:
            continue
        try:
            # Attempt to open candidate port and check for banner/data
            with serial.Serial(device, config.SERIAL_BAUDRATE, timeout=0.5) as ser:
                # Wait briefly for Arduino reboot / startup print
                time.sleep(0.3)
                # Read up to 200 bytes or until timeout
                data = ser.read(200)
                decoded = data.decode(errors="ignore").upper()
                if "PISOWIFI" in decoded or "PULSES" in decoded or "COIN" in decoded:
                    return device
        except Exception:
            pass

    # Fallback to the highest-scoring candidate if no active banner was probed
    return candidates[0][1]
