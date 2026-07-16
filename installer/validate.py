import os
import sys
import platform
from installer.utils import run_cmd


def validate_system_version() -> tuple[bool, list[str]]:
    """
    Validates OS and Python version compatibility.
    """
    success = True
    messages = []

    # 1. Python version check (>= 3.9)
    py_ver = sys.version_info
    if py_ver.major < 3 or (py_ver.major == 3 and py_ver.minor < 9):
        success = False
        messages.append(f"Python version {platform.python_version()} is not supported. Require >= 3.9.")
    else:
        messages.append(f"Python version: {platform.python_version()} (OK)")

    # 2. OS release check (Ubuntu >= 20.04 or Debian >= 11)
    if os.path.exists("/etc/os-release"):
        os_info = {}
        with open("/etc/os-release") as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    os_info[key] = val.strip('"')

        distro = os_info.get("ID", "").lower()
        ver_id = os_info.get("VERSION_ID", "")

        if distro in ["ubuntu", "debian"]:
            try:
                if distro == "ubuntu":
                    major_ver = float(ver_id.split(".")[0])
                    if major_ver < 20:
                        success = False
                        messages.append(f"Ubuntu version {ver_id} is unsupported. Require >= 20.04.")
                    else:
                        messages.append(f"OS Distro: {os_info.get('PRETTY_NAME', 'Ubuntu')} (OK)")
                elif distro == "debian":
                    major_ver = int(ver_id.split(".")[0])
                    if major_ver < 11:
                        success = False
                        messages.append(f"Debian version {ver_id} is unsupported. Require >= 11.")
                    else:
                        messages.append(f"OS Distro: {os_info.get('PRETTY_NAME', 'Debian')} (OK)")
            except ValueError:
                messages.append(f"Warning: Could not parse OS version ID: {ver_id}")
        else:
            messages.append(f"Warning: Untested OS distro '{distro}'. PisoWiFi is validated on Ubuntu/Debian.")
    else:
        messages.append("Warning: /etc/os-release not found. OS compatibility check skipped.")

    return success, messages


def validate_kernel_capabilities() -> tuple[bool, list[str]]:
    """
    Validates Kernel module capability support (sch_htb, ifb, act_mirred).
    """
    success = True
    messages = []

    required_modules = ["sch_htb", "ifb", "act_mirred"]

    for mod in required_modules:
        if os.path.exists(f"/sys/module/{mod}"):
            messages.append(f"Kernel module '{mod}': Loaded/Available (OK)")
        else:
            res = run_cmd(["modprobe", "--dry-run", mod])
            if res.returncode == 0:
                messages.append(f"Kernel module '{mod}': Available (OK)")
            else:
                success = False
                messages.append(f"Warning: Kernel module '{mod}' is not loaded/available. Bandwidth limiting might fail.")

    return success, messages
