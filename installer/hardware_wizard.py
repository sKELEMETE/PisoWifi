from __future__ import annotations

import json

from installer.hardware import (
    ORANGE_PI_PC_PROFILE,
    capture_pulse_burst,
    detect_host,
    is_verified_orange_pi_pc,
    powered_relay,
    read_gpio_lines,
    resolve_profile_pin,
    test_relay,
)


SAFETY_WARNING = """WARNING:
DO NOT CONNECT THE 12V COIN SELECTOR SIGNAL
DIRECTLY TO THE ORANGE PI GPIO."""


def _yes_no(question: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    answer = input(question + suffix).strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def _select_pin(label: str, recommended: int, lines: list[dict]) -> dict:
    default = resolve_profile_pin(recommended, lines)
    print(f"\nRecommended {label}:")
    print(f"  Physical pin : {default['physical_pin']}")
    print(f"  GPIO         : {default['gpio_name']}")
    print(f"  gpiochip     : {default['chip']}")
    print(f"  offset       : {default['offset']}")
    choice = input(f"Physical pin for {label} [Enter = {recommended}]: ").strip()
    return resolve_profile_pin(int(choice), lines) if choice else default


def _calibrate(coin_pin: dict, edge: str, debounce_ms: int, gap_ms: int, currency: str) -> dict[int, int]:
    count_text = input("How many denominations do you want to configure? [0]: ").strip()
    denomination_count = int(count_text or "0")
    if not 0 <= denomination_count <= 20:
        raise ValueError("Denomination count must be between 0 and 20")
    mapping: dict[int, int] = {}
    for _ in range(denomination_count):
        value = int(input(f"Enter denomination value (shown as {currency}<value>): ").strip())
        if not 1 <= value <= 1000:
            raise ValueError("Denomination must be between 1 and 1000")
        samples = []
        for attempt in range(1, 4):
            print(f"Insert {currency}{value} now (attempt {attempt}/3)...")
            pulses = capture_pulse_burst(
                coin_pin["chip"], coin_pin["offset"], edge, debounce_ms, gap_ms
            )
            print(f"  Attempt {attempt}: {pulses} pulse(s)")
            samples.append(pulses)
        if 0 in samples or len(set(samples)) != 1:
            print(f"[WARNING] Samples disagree ({samples}); {currency}{value} was not saved.")
            continue
        pulses = samples[0]
        if pulses in mapping and mapping[pulses] != value:
            print(f"[WARNING] {pulses} pulse(s) is already mapped; denomination was not saved.")
            continue
        if _yes_no(f"Accept {pulses} pulse(s) -> {currency}{value}?", default=True):
            mapping[pulses] = value
    return mapping


def run_hardware_wizard(non_interactive: bool, skip_hardware_test: bool, requested_interface: str | None = None) -> tuple[dict[str, str], dict]:
    host = detect_host()
    print("\n================================================")
    print("        PisoWiFi Hardware Configuration")
    print("================================================")
    print(f"Detected board : {host['board']}")
    print(f"Detected OS    : {host['os']} ({host['codename'] or 'unknown codename'})")
    print(f"Architecture   : {host['architecture']}")
    print(f"GPIO subsystem : {host['gpio_subsystem']}")
    print(f"\n{SAFETY_WARNING}\n")

    interface = requested_interface
    if not interface and non_interactive:
        interface = "arduino"
    if not interface:
        print("Coin interface:\n  1. Arduino via USB serial\n  2. Native Orange Pi GPIO")
        interface = "gpio" if input("Select [1/2] [1]: ").strip() == "2" else "arduino"

    if interface == "arduino":
        return {"COIN_INTERFACE": "arduino"}, {"host": host, "interface": "arduino"}

    if not is_verified_orange_pi_pc(host):
        raise RuntimeError(
            "GPIO auto-configuration stopped: the host is not confidently identified as Orange Pi PC running Debian 13 Trixie. "
            f"Detected board={host['board']!r}, OS={host['os']!r}, architecture={host['architecture']!r}."
        )
    if host["gpio_subsystem"] != "libgpiod":
        raise RuntimeError("GPIO auto-configuration stopped: gpiodetect/gpioinfo are unavailable")
    if non_interactive:
        raise RuntimeError("Native GPIO setup requires the interactive electrical-safety confirmations")

    print("Before GPIO mode can continue, verify the external interfaces.")
    if not _yes_no("Is the coin pulse interface verified to limit the GPIO side to safe 3.3V logic?"):
        raise RuntimeError("GPIO setup stopped: install and verify an optocoupler or other 3.3V-safe pulse interface")
    if not _yes_no("Is the relay IN interface verified to accept 3.3V logic (or driven through a transistor/opto interface)?"):
        raise RuntimeError("GPIO setup stopped: use a verified 3.3V-compatible relay driver/interface")
    if not _yes_no("Is the relay driver input biased to the OFF state while the Orange Pi GPIO is unpowered or unclaimed?"):
        raise RuntimeError("GPIO setup stopped: add a correctly sized fail-safe pull-up/pull-down in the verified relay driver design")

    lines = read_gpio_lines()
    coin_pin = _select_pin("coin input", ORANGE_PI_PC_PROFILE["recommended_coin_pin"], lines)
    relay_pin = _select_pin("relay output", ORANGE_PI_PC_PROFILE["recommended_relay_pin"], lines)
    if coin_pin["physical_pin"] == relay_pin["physical_pin"]:
        raise RuntimeError("Coin input and relay output must use different GPIO lines")

    edge = "rising" if input("Coin pulse active edge [falling/rising] [falling]: ").strip().lower() == "rising" else "falling"
    active_low = input("Relay active state [low/high] [low]: ").strip().lower() != "high"
    debounce_ms = 20
    gap_ms = 250
    relay_tested = False
    coin_tested = False
    mapping: dict[int, int] = {}

    if not skip_hardware_test:
        print("\nRelay test\n----------")
        print("Disconnect the 12V load if desired. Never feed 5V or 12V into an Orange Pi GPIO.")
        if _yes_no("Toggle relay for testing?"):
            test_relay(relay_pin["chip"], relay_pin["offset"], active_low)
            relay_tested = _yes_no("Did the relay switch ON and then return OFF as expected?")

        print("\nCoin Selector Calibration\n--------------------------")
        print(SAFETY_WARNING)
        if _yes_no("Calibrate the isolated coin pulse input now?"):
            currency = input("Currency symbol [₱]: ").strip() or "₱"
            if len(currency) > 8 or any(char in currency for char in "\r\n="):
                raise ValueError("Currency symbol must be 1-8 characters and cannot contain '=' or a newline")
            print("Powering the coin selector during calibration...")
            with powered_relay(relay_pin["chip"], relay_pin["offset"], active_low):
                mapping = _calibrate(coin_pin, edge, debounce_ms, gap_ms, currency)
            coin_tested = bool(mapping)
        else:
            currency = "₱"
    else:
        currency = "₱"

    settings = {
        "COIN_INTERFACE": "gpio",
        "GPIO_COIN_CHIP": coin_pin["chip"],
        "GPIO_COIN_LINE": str(coin_pin["offset"]),
        "GPIO_COIN_NAME": coin_pin["gpio_name"],
        "GPIO_COIN_PHYSICAL_PIN": str(coin_pin["physical_pin"]),
        "GPIO_COIN_EDGE": edge,
        "GPIO_RELAY_CHIP": relay_pin["chip"],
        "GPIO_RELAY_LINE": str(relay_pin["offset"]),
        "GPIO_RELAY_NAME": relay_pin["gpio_name"],
        "GPIO_RELAY_PHYSICAL_PIN": str(relay_pin["physical_pin"]),
        "GPIO_RELAY_ACTIVE_LOW": str(active_low).lower(),
        "COIN_DEBOUNCE_MS": str(debounce_ms),
        "COIN_INTER_PULSE_GAP_MS": str(gap_ms),
        "COIN_SESSION_LEASE_SECONDS": "12",
        "COIN_HEARTBEAT_SECONDS": "3",
        "COIN_CURRENCY_SYMBOL": currency,
        "COIN_PULSE_MAP": json.dumps(mapping, separators=(",", ":")),
    }
    summary = {
        "host": host,
        "interface": "gpio",
        "coin_pin": coin_pin,
        "relay_pin": relay_pin,
        "active_low": active_low,
        "mapping": mapping,
        "relay_tested": relay_tested,
        "coin_tested": coin_tested,
    }
    return settings, summary


def print_completion_hardware(summary: dict, config_path: str, log_path: str) -> None:
    if summary.get("interface") != "gpio":
        print("Hardware backend: Arduino via USB serial (existing mode preserved)")
        return

    required_details = {
        "coin_pin", "relay_pin", "active_low", "mapping",
        "relay_tested", "coin_tested",
    }
    if not required_details.issubset(summary) or not summary.get("host", {}).get("board"):
        print("\nHardware backend: Native GPIO (existing configuration preserved)")
        print(f"Configuration: {config_path}\nInstallation log: {log_path}")
        print("Useful commands:\n  sudo pisowifi doctor\n  sudo pisowifi hardware-status\n  sudo pisowifi hardware-test")
        return

    coin = summary["coin_pin"]
    relay = summary["relay_pin"]
    state = "LOW" if summary["active_low"] else "HIGH"
    print("\n============================================================")
    print("             PisoWiFi Installation Complete")
    print("============================================================")
    print(f"BOARD\n  {summary['host']['board']}")
    print("\nCOIN INPUT")
    print(f"  Physical header pin : {coin['physical_pin']}\n  GPIO name           : {coin['gpio_name']}\n  gpiochip            : {coin['chip']}\n  line offset         : {coin['offset']}")
    print(f"\n{SAFETY_WARNING}")
    print(f"\n  Coin WHITE/GRAY -> optocoupler / verified 3.3V-safe interface -> physical pin {coin['physical_pin']}")
    print("  Verified open-collector alternative:")
    print(f"    Physical pin 17 (3.3V) -> 10k pull-up -> physical pin {coin['physical_pin']}")
    print(f"    Coin WHITE -> 1k series resistor -> physical pin {coin['physical_pin']}")
    print("    Coin BLACK / 12V PSU GND -> Orange Pi physical pin 34 GND")
    print("  Use this alternative only after verifying the selector output is open-collector and 3.3V-safe.")
    print("\nRELAY CONTROL")
    print(f"  Physical header pin : {relay['physical_pin']}\n  GPIO name           : {relay['gpio_name']}\n  gpiochip            : {relay['chip']}\n  line offset         : {relay['offset']}\n  active state        : {state}")
    print("\nRELAY POWER WIRING")
    print("  12V PSU + -> Relay COM\n  Relay NO -> Coin Selector RED\n  Coin Selector BLACK -> 12V PSU GND")
    print(f"\nRELAY CONTROL\n  Orange Pi physical pin {relay['physical_pin']} -> verified relay driver/input")
    print("  Relay VCC -> appropriate 5V supply; relay/driver GND -> the control ground required by its verified design")
    print("  Verify that relay IN accepts 3.3V logic; otherwise use a transistor/driver/opto interface.")
    print("  The driver must also default OFF while GPIO is unpowered/unclaimed (use the correct fail-safe bias).")
    print("\nConfigured coin mappings:")
    if summary["mapping"]:
        for pulses, value in sorted(summary["mapping"].items()):
            print(f"  {pulses} pulse(s) -> {value}")
    else:
        print("  NONE — run 'sudo pisowifi hardware-test --calibrate' before accepting coins")
    print("\nTest status:")
    print(f"  Relay ........... {'OK' if summary['relay_tested'] else 'NOT TESTED'}")
    print(f"  Coin input ...... {'OK' if summary['coin_tested'] else 'NOT TESTED'}")
    print("  GPIO ............ CONFIGURED (live operation not asserted)")
    print(f"\nConfiguration: {config_path}\nInstallation log: {log_path}")
    print("\nUseful commands:\n  sudo pisowifi doctor\n  sudo pisowifi hardware-status\n  sudo pisowifi hardware-test")
    print("============================================================")
