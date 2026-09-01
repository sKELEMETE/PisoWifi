from __future__ import annotations

import json
import os
import subprocess
import sys

import httpx

from installer.hardware import capture_pulse_burst, detect_host, line_matches_config, powered_relay, read_gpio_lines, test_relay
from installer.hardware_wizard import SAFETY_WARNING, _calibrate, _yes_no


def _config():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(base_dir, "backend"))
    import config
    return config


def hardware_status() -> bool:
    config = _config()
    host = detect_host()
    print(f"Board             : {host['board']}")
    print(f"OS                : {host['os']}")
    print(f"Architecture      : {host['architecture']}")
    print(f"Coin backend      : {config.COIN_INTERFACE}")
    if config.COIN_INTERFACE == "arduino":
        print(f"Serial device     : {config.SERIAL_PORT or 'AUTO'}")
        return True

    print(f"Coin input        : physical {config.GPIO_COIN_PHYSICAL_PIN}, {config.GPIO_COIN_NAME}, {config.GPIO_COIN_CHIP} offset {config.GPIO_COIN_LINE}")
    print(f"Relay output      : physical {config.GPIO_RELAY_PHYSICAL_PIN}, {config.GPIO_RELAY_NAME}, {config.GPIO_RELAY_CHIP} offset {config.GPIO_RELAY_LINE}")
    print(f"Relay active      : {'LOW' if config.GPIO_RELAY_ACTIVE_LOW else 'HIGH'}")
    print(f"Pulse mapping     : {json.dumps(config.COIN_PULSE_MAP, sort_keys=True)}")
    lines = read_gpio_lines()
    for label, chip, offset, name in (
        ("coin", config.GPIO_COIN_CHIP, config.GPIO_COIN_LINE, config.GPIO_COIN_NAME),
        ("relay", config.GPIO_RELAY_CHIP, config.GPIO_RELAY_LINE, config.GPIO_RELAY_NAME),
    ):
        found = next((line for line in lines if line_matches_config(line, chip, offset, name)), None)
        print(f"{label.title()} line live    : {'FOUND' if found else 'NOT FOUND'}")
    try:
        response = httpx.get(f"http://127.0.0.1:{config.BACKEND_PORT}/api/v1/coin/hardware-status", timeout=2)
        response.raise_for_status()
        state = response.json().get("data", {})
        if not state:
            raise RuntimeError("backend returned no hardware state")
        print(f"Relay state       : {'ON' if state.get('relay_on') else 'OFF'}")
        print(f"Coin lease        : {'ACTIVE' if state.get('coin_session_active') else 'INACTIVE'}")
    except Exception as exc:
        print(f"Backend state     : unavailable ({exc})")
    return True


def _update_mapping(config, mapping: dict[int, int]) -> None:
    env_path = os.path.join(config.BASE_DIR, "backend", ".env")
    with open(env_path) as stream:
        lines = stream.readlines()
    replacement = f"COIN_PULSE_MAP={json.dumps(mapping, separators=(',', ':'))}\n"
    updated = []
    found = False
    for line in lines:
        if line.startswith("COIN_PULSE_MAP="):
            updated.append(replacement)
            found = True
        else:
            updated.append(line)
    if not found:
        updated.append(replacement)
    temp_path = env_path + ".tmp"
    with open(temp_path, "w") as stream:
        stream.writelines(updated)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, env_path)


def hardware_test(calibrate: bool = False) -> bool:
    if os.geteuid() != 0:
        print("Run hardware-test with sudo so services and GPIO lines can be controlled safely.")
        return False
    config = _config()
    if config.COIN_INTERFACE != "gpio":
        print("Hardware test is for native GPIO mode; Arduino mode remains configured.")
        return False
    print(SAFETY_WARNING)
    if not _yes_no("Have you verified the pulse and relay interfaces are 3.3V-safe?"):
        print("Test cancelled.")
        return False

    subprocess.run(["systemctl", "stop", "pisowifi-coin", "pisowifi-backend"], check=True)
    try:
        test_relay(config.GPIO_RELAY_CHIP, config.GPIO_RELAY_LINE, config.GPIO_RELAY_ACTIVE_LOW)
        relay_ok = _yes_no("Did the relay switch ON and return OFF correctly?")
        print("Powering the coin selector during pulse testing...")
        with powered_relay(config.GPIO_RELAY_CHIP, config.GPIO_RELAY_LINE, config.GPIO_RELAY_ACTIVE_LOW):
            if calibrate:
                mapping = _calibrate(
                    {"chip": config.GPIO_COIN_CHIP, "offset": config.GPIO_COIN_LINE},
                    config.GPIO_COIN_EDGE,
                    config.COIN_DEBOUNCE_MS,
                    config.COIN_INTER_PULSE_GAP_MS,
                    config.COIN_CURRENCY_SYMBOL,
                )
                if mapping:
                    _update_mapping(config, mapping)
                    print("Calibration mapping saved.")
                coin_ok = bool(mapping)
            else:
                print("Insert one test coin now; only the isolated input is observed and no credit is created.")
                pulses = capture_pulse_burst(
                    config.GPIO_COIN_CHIP,
                    config.GPIO_COIN_LINE,
                    config.GPIO_COIN_EDGE,
                    config.COIN_DEBOUNCE_MS,
                    config.COIN_INTER_PULSE_GAP_MS,
                )
                coin_ok = pulses > 0
                print(f"Observed pulse count: {pulses}" if coin_ok else "No pulse observed.")
        return relay_ok and coin_ok
    finally:
        subprocess.run(["systemctl", "start", "pisowifi-backend", "pisowifi-coin"], check=False)
