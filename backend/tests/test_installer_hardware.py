import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from installer import hardware
from installer.hardware import is_verified_orange_pi_pc, read_gpio_lines, resolve_profile_pin


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
    monkeypatch.setattr(
        hardware.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 0, "stdout": output})(),
    )
    lines = read_gpio_lines()
    assert lines[0]["chip"] == "/dev/gpiochip2"
    assert lines[0]["available"] is True
    assert lines[1]["available"] is False
