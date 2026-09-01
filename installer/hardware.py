from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta
from contextlib import contextmanager
import os
import platform
import re
import shutil
import subprocess
import time


@dataclass(frozen=True)
class HeaderPin:
    physical_pin: int
    gpio_name: str
    legacy_linux_gpio: int
    capabilities: tuple[str, ...]
    alternate_function: str


ORANGE_PI_PC_PINS = {
    29: HeaderPin(29, "PA7", 7, ("input", "output", "edge"), "GPIO / EINT7"),
    31: HeaderPin(31, "PA8", 8, ("input", "output", "edge"), "GPIO / EINT8"),
    33: HeaderPin(33, "PA9", 9, ("input", "output", "edge"), "GPIO / EINT9"),
    35: HeaderPin(35, "PA10", 10, ("input", "output", "edge"), "GPIO / EINT10"),
    37: HeaderPin(37, "PA20", 20, ("input", "output", "edge"), "GPIO / EINT20"),
}

ORANGE_PI_PC_PROFILE = {
    "model": "Orange Pi PC",
    "soc": "Allwinner H3",
    "recommended_coin_pin": 29,
    "recommended_relay_pin": 33,
    "pins": ORANGE_PI_PC_PINS,
}

H3_MAIN_GPIO_LABEL = "1c20800.pinctrl"


def _read_text(path: str) -> str:
    try:
        with open(path, "rb") as stream:
            return stream.read().replace(b"\x00", b"").decode(errors="replace").strip()
    except OSError:
        return ""


def detect_host() -> dict[str, str]:
    os_release = {}
    for line in _read_text("/etc/os-release").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            os_release[key] = value.strip().strip('"')
    architecture = platform.machine()
    dpkg = shutil.which("dpkg")
    if dpkg:
        result = subprocess.run([dpkg, "--print-architecture"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            architecture = result.stdout.strip()
    return {
        "board": _read_text("/proc/device-tree/model") or "Unknown",
        "os": os_release.get("PRETTY_NAME", platform.platform()),
        "os_id": os_release.get("ID", ""),
        "version_id": os_release.get("VERSION_ID", ""),
        "codename": os_release.get("VERSION_CODENAME", ""),
        "architecture": architecture,
        "kernel": platform.release(),
        "gpio_subsystem": "libgpiod" if shutil.which("gpiodetect") else "not detected",
    }


def is_verified_orange_pi_pc(host: dict[str, str]) -> bool:
    model = host["board"].lower().replace("xunlong", "").strip()
    board_ok = model == "orange pi pc"
    return board_ok and host["os_id"] == "debian" and host["version_id"] == "13" and host["codename"] == "trixie"


def read_gpio_chips() -> dict[str, dict]:
    gpiodetect = shutil.which("gpiodetect")
    if not gpiodetect:
        return {}
    result = subprocess.run([gpiodetect], capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    chips = {}
    for raw in result.stdout.splitlines():
        match = re.match(r"\s*(gpiochip\d+)\s+\[([^]]+)]\s+\((\d+)\s+lines\)", raw)
        if match:
            chips[f"/dev/{match.group(1)}"] = {
                "label": match.group(2),
                "line_count": int(match.group(3)),
            }
    return chips


def read_gpio_lines() -> list[dict]:
    gpioinfo = shutil.which("gpioinfo")
    if not gpioinfo:
        return []
    result = subprocess.run([gpioinfo], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    chips = read_gpio_chips()
    lines = []
    chip = None
    for raw in result.stdout.splitlines():
        header = re.match(r"\s*(?:/dev/)?(gpiochip\d+)\s+-\s+\d+\s+lines", raw)
        if header:
            chip = f"/dev/{header.group(1)}"
            continue
        match = re.match(r'\s*line\s+(\d+):\s+"?([^"\s]+)"?\s+(.*)', raw)
        if chip and match:
            details = match.group(3)
            old_consumer = details.lstrip().startswith('"')
            lines.append({
                "chip": chip,
                "offset": int(match.group(1)),
                "name": match.group(2),
                "controller": chips.get(chip, {}).get("label", ""),
                "line_count": chips.get(chip, {}).get("line_count", 0),
                "available": "consumer=" not in details and "[used]" not in details and not old_consumer,
                "details": details.strip(),
            })
    return lines


def line_matches_config(line: dict, chip: str, offset: int, gpio_name: str) -> bool:
    if line["chip"] != chip or line["offset"] != offset:
        return False
    if line["name"].upper() == gpio_name.upper():
        return True
    pin = next((item for item in ORANGE_PI_PC_PINS.values() if item.gpio_name == gpio_name.upper()), None)
    return bool(
        pin
        and line["name"].lower() == "unnamed"
        and line.get("controller") == H3_MAIN_GPIO_LABEL
        and line.get("line_count") == 224
        and offset == pin.legacy_linux_gpio
    )


def resolve_profile_pin(physical_pin: int, lines: list[dict] | None = None) -> dict:
    pin = ORANGE_PI_PC_PINS.get(physical_pin)
    if not pin:
        raise ValueError(f"Physical pin {physical_pin} is not in the maintained Orange Pi PC safe-GPIO list")
    live_lines = lines or read_gpio_lines()
    matches = [line for line in live_lines if line["name"].upper() == pin.gpio_name]
    if not matches:
        matches = [
            line for line in live_lines
            if line["name"].lower() == "unnamed"
            and line.get("controller") == H3_MAIN_GPIO_LABEL
            and line.get("line_count") == 224
            and line["offset"] == pin.legacy_linux_gpio
        ]
    if len(matches) != 1:
        raise RuntimeError(f"Could not uniquely resolve {pin.gpio_name} from live gpioinfo output")
    resolved = {**asdict(pin), **matches[0]}
    if not resolved["available"]:
        raise RuntimeError(f"{pin.gpio_name} on physical pin {physical_pin} is already in use: {resolved['details']}")
    return resolved


def capture_pulse_burst(chip: str, offset: int, edge_name: str, debounce_ms: int, gap_ms: int, timeout: int = 15) -> int:
    try:
        import gpiod
        from gpiod.line import Direction, Edge
    except ImportError as exc:
        raise RuntimeError("python3-libgpiod is not installed") from exc
    edge = Edge.RISING if edge_name == "rising" else Edge.FALLING
    settings = gpiod.LineSettings(
        direction=Direction.INPUT,
        edge_detection=edge,
        debounce_period=timedelta(milliseconds=debounce_ms),
    )
    count = 0
    last_event = None
    deadline = time.monotonic() + timeout
    try:
        request_context = gpiod.request_lines(chip, consumer="pisowifi-calibration", config={offset: settings})
    except OSError:
        settings = gpiod.LineSettings(direction=Direction.INPUT, edge_detection=edge)
        request_context = gpiod.request_lines(chip, consumer="pisowifi-calibration", config={offset: settings})
    with request_context as request:
        while time.monotonic() < deadline:
            wait = gap_ms / 1000 if count else min(1, deadline - time.monotonic())
            if not request.wait_edge_events(timedelta(seconds=max(0, wait))):
                if count and last_event is not None:
                    break
                continue
            events = request.read_edge_events()
            count += len(events)
            last_event = time.monotonic()
    return count


def test_relay(chip: str, offset: int, active_low: bool, prompt=input) -> bool:
    try:
        import gpiod
        from gpiod.line import Direction, Value
    except ImportError as exc:
        raise RuntimeError("python3-libgpiod is not installed") from exc
    off = Value.ACTIVE if active_low else Value.INACTIVE
    on = Value.INACTIVE if active_low else Value.ACTIVE
    settings = gpiod.LineSettings(direction=Direction.OUTPUT, output_value=off)
    with gpiod.request_lines(chip, consumer="pisowifi-relay-test", config={offset: settings}) as request:
        try:
            request.set_value(offset, on)
            prompt("Turning relay ON. Press Enter after verifying its state: ")
            request.set_value(offset, off)
            prompt("Relay is OFF. Press Enter after verifying its state: ")
            return True
        finally:
            request.set_value(offset, off)


@contextmanager
def powered_relay(chip: str, offset: int, active_low: bool, gpio_api=None):
    if gpio_api is None:
        try:
            import gpiod
            from gpiod.line import Direction, Value
        except ImportError as exc:
            raise RuntimeError("python3-libgpiod is not installed") from exc
    else:
        gpiod, Direction, Value = gpio_api
    off = Value.ACTIVE if active_low else Value.INACTIVE
    on = Value.INACTIVE if active_low else Value.ACTIVE
    settings = gpiod.LineSettings(direction=Direction.OUTPUT, output_value=off)
    with gpiod.request_lines(
        chip,
        consumer="pisowifi-calibration-relay",
        config={offset: settings},
    ) as request:
        try:
            request.set_value(offset, on)
            yield
        finally:
            request.set_value(offset, off)
