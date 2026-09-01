import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from installer import hardware
from installer.hardware import is_verified_orange_pi_pc, line_matches_config, powered_relay, read_gpio_lines, resolve_profile_pin


def test_orange_pi_pc_gpio_profile_resolves_live_chip_offsets():
    lines = [
        {"chip": "/dev/gpiochip3", "offset": 7, "name": "PA7", "available": True, "details": "unused input active-high"},
        {"chip": "/dev/gpiochip3", "offset": 9, "name": "PA9", "available": True, "details": "unused input active-high"},
    ]
    coin = resolve_profile_pin(29, lines)
    relay = resolve_profile_pin(33, lines)
    assert (coin["gpio_name"], coin["chip"], coin["offset"]) == ("PA7", "/dev/gpiochip3", 7)
    assert (relay["gpio_name"], relay["chip"], relay["offset"]) == ("PA9", "/dev/gpiochip3", 9)


def test_profile_rejects_used_or_unverified_lines():
    used = [{"chip": "/dev/gpiochip0", "offset": 7, "name": "PA7", "available": False, "details": '"driver" input [used]'}]
    with pytest.raises(RuntimeError):
        resolve_profile_pin(29, used)
    with pytest.raises(ValueError):
        resolve_profile_pin(7, used)


def test_gpio_autoconfiguration_requires_exact_board_and_os():
    valid = {
        "board": "Xunlong Orange Pi PC",
        "os_id": "debian",
        "version_id": "13",
        "codename": "trixie",
    }
    assert is_verified_orange_pi_pc(valid)
    assert not is_verified_orange_pi_pc({**valid, "board": "Orange Pi PC Plus"})
    assert not is_verified_orange_pi_pc({**valid, "codename": "bookworm", "version_id": "12"})


def test_gpioinfo_parser_tracks_runtime_chip_and_consumers(monkeypatch):
    output = """/dev/gpiochip2 - 32 lines:
 line 7: \"PA7\" unused input active-high
 line 9: \"PA9\" \"another-driver\" output active-high [used]
"""
    monkeypatch.setattr(hardware.shutil, "which", lambda name: "/usr/bin/gpioinfo")
    def fake_run(command, **_kwargs):
        stdout = "gpiochip2 [test-controller] (32 lines)\n" if "gpiodetect" in command[0] else output
        return type("Result", (), {"returncode": 0, "stdout": stdout})()

    monkeypatch.setattr(hardware.subprocess, "run", fake_run)
    lines = read_gpio_lines()
    assert lines[0]["chip"] == "/dev/gpiochip2"
    assert lines[0]["available"] is True
    assert lines[1]["available"] is False


def test_unnamed_armbian_h3_lines_resolve_by_verified_controller_and_offset(monkeypatch):
    info = """gpiochip0 - 224 lines:
 line   7: unnamed input
 line   9: unnamed input
 line  15: unnamed output consumer=orangepi:red:status
"""

    def fake_run(command, **_kwargs):
        stdout = "gpiochip0 [1c20800.pinctrl] (224 lines)\n" if "gpiodetect" in command[0] else info
        return type("Result", (), {"returncode": 0, "stdout": stdout})()

    monkeypatch.setattr(hardware.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(hardware.subprocess, "run", fake_run)
    lines = read_gpio_lines()
    coin = resolve_profile_pin(29, lines)
    relay = resolve_profile_pin(33, lines)

    assert (coin["chip"], coin["offset"], coin["gpio_name"]) == ("/dev/gpiochip0", 7, "PA7")
    assert (relay["chip"], relay["offset"], relay["gpio_name"]) == ("/dev/gpiochip0", 9, "PA9")
    assert line_matches_config(lines[0], "/dev/gpiochip0", 7, "PA7")


@pytest.mark.parametrize("active_low,off,on", [(True, 1, 0), (False, 0, 1)])
def test_calibration_relay_is_powered_and_always_returns_off(active_low, off, on):
    class Direction:
        OUTPUT = "output"

    class Value:
        INACTIVE = 0
        ACTIVE = 1

    class Request:
        def __init__(self):
            self.values = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def set_value(self, _offset, value):
            self.values.append(value)

    class Gpiod:
        def __init__(self):
            self.request = Request()
            self.initial = None

        def LineSettings(self, **kwargs):
            self.initial = kwargs["output_value"]
            return kwargs

        def request_lines(self, *_args, **_kwargs):
            return self.request

    api = Gpiod()
    with pytest.raises(RuntimeError):
        with powered_relay("/dev/gpiochip0", 9, active_low, (api, Direction, Value)):
            assert api.initial == off
            assert api.request.values == [on]
            raise RuntimeError("calibration failed")
    assert api.request.values == [on, off]
