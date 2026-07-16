import os
import sys
import subprocess


def get_version() -> str:
    # Resolve path relative to this file
    installer_dir = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(installer_dir, "..", "VERSION")
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            return f.read().strip()
    return "1.6.0"


def check_root() -> bool:
    return os.geteuid() == 0


def run_cmd(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)
