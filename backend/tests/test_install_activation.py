import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import call, patch

import install


def test_cli_launcher_resolves_installed_symlink(tmp_path):
    app_dir = tmp_path / "opt" / "pisowifi"
    launcher = app_dir / "bin" / "pisowifi"
    launcher.parent.mkdir(parents=True)
    shutil.copy(Path(install.SOURCE_DIR) / "bin" / "pisowifi", launcher)
    launcher.chmod(0o755)

    python = app_dir / "backend" / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
    python.chmod(0o755)
    cli = app_dir / "installer" / "cli.py"
    cli.parent.mkdir(parents=True)
    cli.write_text("")

    installed_link = tmp_path / "usr" / "local" / "bin" / "pisowifi"
    installed_link.parent.mkdir(parents=True)
    os.symlink(launcher, installed_link)

    result = subprocess.run(
        [installed_link, "hardware-status"], capture_output=True, text=True, check=True
    )

    assert result.stdout.splitlines() == [str(cli), "hardware-status"]


@patch("install.subprocess.run")
def test_activation_validates_nginx_and_restarts_configured_services(run):
    install.activate_system_services()

    services = (
        "mariadb",
        "pisowifi-network",
        "nftables",
        "dnsmasq",
        "nginx",
        "pisowifi-backend",
        "pisowifi-coin",
    )
    assert run.call_args_list == [
        call(["systemctl", "daemon-reload"], check=True, cwd=None),
        call(["systemctl", "enable", *services], check=True, cwd=None),
        call(["nginx", "-t"], check=True, cwd=None),
        *(call(["systemctl", "restart", service], check=True, cwd=None) for service in services),
    ]
