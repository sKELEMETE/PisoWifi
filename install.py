#!/usr/bin/env python3
import os
import sys
import argparse
import ipaddress
import subprocess
import shutil

# Ensure installer folder is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from installer.utils import get_version, check_root
from installer.validate import validate_system_version, validate_kernel_capabilities
from installer.templates import render_templates, install_system_files
from installer.rollback import RollbackManager
from installer.backup import create_and_validate_backup
from installer.uninstall import run_uninstall
from installer.log_manager import get_logger
from installer.hardware_wizard import print_completion_hardware, run_hardware_wizard

logger = get_logger("install", "install.log")
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_checked(command: list[str], dry_run: bool = False, cwd: str | None = None) -> None:
    if dry_run:
        print(f"[DRY-RUN] Would run: {' '.join(command)}")
        return
    logger.info("Running: %s", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd)


def install_dependencies(dry_run: bool) -> None:
    packages = [
        "mariadb-server", "mariadb-client",
        "python3", "python3-venv", "python3-pip", "python3-bcrypt", "python3-libgpiod", "gpiod",
        "nginx", "dnsmasq", "nftables", "iproute2", "nodejs", "npm",
        "build-essential", "python3-dev", "rustc", "cargo", "pkg-config", "libffi-dev", "libssl-dev",
    ]
    run_checked(["apt-get", "update"], dry_run)
    run_checked(["apt-get", "install", "-y", *packages], dry_run)


def deploy_application(source_dir: str, base_dir: str, dry_run: bool) -> None:
    if os.path.realpath(source_dir) == os.path.realpath(base_dir):
        return
    if dry_run:
        print(f"[DRY-RUN] Would copy application files from {source_dir} to {base_dir}")
        return
    ignore = shutil.ignore_patterns(".git", "node_modules", "venv", "__pycache__", ".pytest_cache", ".env", "pisowifi.db")
    os.makedirs(base_dir, exist_ok=True)
    shutil.copytree(source_dir, base_dir, dirs_exist_ok=True, ignore=ignore)


def install_application_dependencies(base_dir: str, dry_run: bool) -> None:
    backend_dir = os.path.join(base_dir, "backend")
    venv_python = os.path.join(backend_dir, "venv", "bin", "python")
    if not os.path.exists(venv_python):
        run_checked(["python3", "-m", "venv", "--system-site-packages", os.path.join(backend_dir, "venv")], dry_run)
    run_checked([venv_python, "-m", "pip", "install", "-r", os.path.join(backend_dir, "requirements.txt")], dry_run)
    frontend_dir = os.path.join(base_dir, "frontend")
    run_checked(["npm", "ci"], dry_run, cwd=frontend_dir)
    run_checked(["npm", "run", "build"], dry_run, cwd=frontend_dir)
    if not dry_run:
        for directory in ("run", "logs", "backups"):
            os.makedirs(os.path.join(base_dir, directory), exist_ok=True)


def setup_database(base_dir: str, dry_run: bool = False) -> None:
    setup_script = os.path.join(base_dir, "scripts", "setup_mariadb.sh")
    if os.path.exists(setup_script):
        if not dry_run:
            os.chmod(setup_script, 0o755)
        run_checked([setup_script], dry_run)
    backend_dir = os.path.join(base_dir, "backend")
    venv_alembic = os.path.join(backend_dir, "venv", "bin", "alembic")
    if os.path.exists(venv_alembic):
        run_checked([venv_alembic, "upgrade", "head"], dry_run, cwd=backend_dir)


def activate_system_services(dry_run: bool = False) -> None:
    services = (
        "mariadb",
        "pisowifi-network",
        "nftables",
        "dnsmasq",
        "nginx",
        "pisowifi-backend",
        "pisowifi-coin",
    )
    run_checked(["systemctl", "daemon-reload"], dry_run)
    run_checked(["systemctl", "enable", *services], dry_run)
    run_checked(["nginx", "-t"], dry_run)
    for service in services:
        run_checked(["systemctl", "restart", service], dry_run)


def read_env(path: str) -> dict[str, str]:
    values = {}
    if not os.path.exists(path):
        return values
    with open(path) as stream:
        for raw in stream:
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def build_env_content(existing: dict[str, str], updates: dict[str, str]) -> str:
    merged = {**existing, **updates}
    return "# PisoWiFi Environment Settings\n" + "".join(f"{key}={value}\n" for key, value in sorted(merged.items()))


def get_interfaces() -> list[str]:
    interfaces = []
    try:
        interfaces = os.listdir("/sys/class/net")
    except Exception:
        pass
    return [i for i in interfaces if i != "lo"]


def detect_wan_interface() -> str | None:
    try:
        with open("/proc/net/route") as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if len(parts) >= 4 and parts[1] == "00000000" and parts[3] == "0002":
                    return parts[0]
    except Exception:
        pass
    return None


def detect_lan_interface(wan: str | None) -> str | None:
    iface_list = get_interfaces()
    if not iface_list:
        return "eth1"
    candidates = [i for i in iface_list if i != wan and not i.startswith("ifb") and not i.startswith("br-")]
    if candidates:
        return candidates[0]
    return iface_list[0]


def main():
    parser = argparse.ArgumentParser(description="PisoWiFi Production Deployment Installation Wizard")
    parser.add_argument("--non-interactive", action="store_true", help="Run without user interaction")
    parser.add_argument("--base-dir", default="/opt/pisowifi", help="Base installation directory")
    parser.add_argument("--lan-interface", help="LAN interface facing captive clients")
    parser.add_argument("--wan-interface", help="WAN interface facing internet gateway")
    parser.add_argument("--gateway-ip", default="10.0.0.1", help="Gateway IP for captive portal clients")
    parser.add_argument("--subnet-mask", default="255.255.255.0", help="Subnet mask for local LAN network")
    parser.add_argument("--dhcp-start", default="10.0.0.20", help="DHCP IP allocation range start")
    parser.add_argument("--dhcp-end", default="10.0.0.254", help="DHCP IP allocation range end")
    parser.add_argument("--backend-port", type=int, default=8000, help="Local port for Uvicorn API backend")
    parser.add_argument("--captive-portal-port", type=int, default=80, help="Web port for Nginx HTTP Server")
    parser.add_argument("--serial-port", default="AUTO", help="Coin acceptor serial device path")
    parser.add_argument("--write-system-configs", action="store_true", default=None, help="Write compiled configs directly to /etc")
    parser.add_argument("--no-system-configs", action="store_false", dest="write_system_configs", help="Do not write configurations to /etc")
    parser.add_argument("--skip-system-checks", action="store_true", help="Skip OS compatibility and kernel capability checks")
    
    # Phase 2 CLI options
    parser.add_argument("--dry-run", action="store_true", help="Perform checks and config generation, but do not write any files")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall PisoWiFi services and configurations")
    parser.add_argument("--preserve-data", action="store_true", default=True, help="Preserve database/logs during uninstall")
    parser.add_argument("--purge", action="store_false", dest="preserve_data", help="Purge all user database records and configurations during uninstall")
    parser.add_argument("--inject-failure-step", type=str, help="For testing: inject failure at a specific install step ('env', 'render', 'system_files')")
    parser.add_argument("--coin-interface", choices=("arduino", "gpio"), help="Select coin hardware backend")
    parser.add_argument("--skip-hardware-test", action="store_true", help="Configure hardware without live relay/calibration tests")
    parser.add_argument("--reconfigure-hardware", action="store_true", help="Run hardware selection even on an existing installation")

    args = parser.parse_args()
    if args.write_system_configs is None:
        args.write_system_configs = check_root() and not args.dry_run

    # Handle uninstall command
    if args.uninstall:
        run_uninstall(args.base_dir, preserve_data=args.preserve_data)
        sys.exit(0)

    # Verify root execution for writing system configs
    if args.write_system_configs and not args.dry_run and not check_root():
        print("[Error] You must run as root to write configurations to /etc system folders.")
        sys.exit(1)

    print("==================================================")
    print(f"      PISOWIFI DEPLOYMENT WIZARD (v{get_version()})       ")
    if args.dry_run:
        print("                  *** DRY RUN ***                ")
    print("==================================================")

    # Run system checks unless skipped
    if not args.skip_system_checks:
        print("\n[System Check] Validating system compatibility...")
        os_ok, os_msgs = validate_system_version()
        for msg in os_msgs:
            print(f"  - {msg}")

        kernel_ok, kernel_msgs = validate_kernel_capabilities()
        for msg in kernel_msgs:
            print(f"  - {msg}")

        if not os_ok:
            print("\n[Error] System version requirements failed. Aborting installation.")
            print("To override this check and proceed anyway, use: --skip-system-checks")
            sys.exit(1)
        print("[System Check] Completed.")

    # Run backup validation if updating an existing install (i.e. if base directory configs already exist)
    if not args.dry_run:
        env_file_check = os.path.join(args.base_dir, "backend", ".env")
        if os.path.exists(env_file_check):
            print("\n[Backup] Existing installation detected. Performing pre-install validation backup...")
            try:
                backup_dir = os.path.join(args.base_dir, "backups")
                backup_path = create_and_validate_backup(args.base_dir, backup_dir)
                if backup_path:
                    print(f"[Backup] Pre-install backup created and validated: {backup_path}")
            except Exception as e:
                print(f"\n[CRITICAL ERROR] Pre-install backup validation failed: {e}")
                print("Aborting installation to prevent configuration loss.")
                sys.exit(1)

    if args.write_system_configs:
        print("\n[Dependencies] Installing Debian packages...")
        install_dependencies(args.dry_run)

    # Detect values
    detected_wan = detect_wan_interface()
    detected_lan = detect_lan_interface(detected_wan)
    interfaces = get_interfaces()

    if not args.non_interactive:
        print("\nPlease configure the installation options:\n")

        base_dir = input(f"Base installation folder [{args.base_dir}]: ").strip()
        if base_dir:
            args.base_dir = base_dir

        wan_default = detected_wan or "eth0"
        print(f"Detected interfaces: {', '.join(interfaces)}")
        wan_interface = input(f"WAN (Internet-facing) interface [{wan_default}]: ").strip()
        args.wan_interface = wan_interface if wan_interface else wan_default

        lan_default = detected_lan or "eth1"
        lan_interface = input(f"LAN (Client-facing) interface [{lan_default}]: ").strip()
        args.lan_interface = lan_interface if lan_interface else lan_default

        gateway_ip = input(f"Gateway IP address [{args.gateway_ip}]: ").strip()
        if gateway_ip:
            args.gateway_ip = gateway_ip

        subnet_mask = input(f"Subnet mask [{args.subnet_mask}]: ").strip()
        if subnet_mask:
            args.subnet_mask = subnet_mask

        dhcp_start = input(f"DHCP start IP [{args.dhcp_start}]: ").strip()
        if dhcp_start:
            args.dhcp_start = dhcp_start
        dhcp_end = input(f"DHCP end IP [{args.dhcp_end}]: ").strip()
        if dhcp_end:
            args.dhcp_end = dhcp_end

        backend_port = input(f"Backend API Uvicorn Port [{args.backend_port}]: ").strip()
        if backend_port:
            try:
                args.backend_port = int(backend_port)
            except ValueError:
                print(f"[Warning] Invalid port '{backend_port}', using default {args.backend_port}")
        portal_port = input(f"Nginx Web Port [{args.captive_portal_port}]: ").strip()
        if portal_port:
            try:
                args.captive_portal_port = int(portal_port)
            except ValueError:
                print(f"[Warning] Invalid port '{portal_port}', using default {args.captive_portal_port}")

    else:
        if not args.lan_interface:
            args.lan_interface = detected_lan or "eth1"
        if not args.wan_interface:
            args.wan_interface = detected_wan or "eth0"

    try:
        net = ipaddress.IPv4Network(f"{args.gateway_ip}/{args.subnet_mask}", strict=False)
        subnet_cidr = str(net)
        gateway_prefix = net.prefixlen
    except Exception:
        subnet_cidr = f"{args.gateway_ip}/24"
        gateway_prefix = 24

    if args.lan_interface == args.wan_interface and not args.dry_run:
        print("[Error] WAN and LAN interfaces must be different; refusing to reconfigure the internet-facing interface as the captive LAN.")
        sys.exit(1)

    existing_env_path = os.path.join(args.base_dir, "backend", ".env")
    existing_env = read_env(existing_env_path)
    existing_interface = existing_env.get("COIN_INTERFACE", "arduino").strip("'\"") if existing_env else None
    stopped_for_reconfigure = False
    if existing_env and not args.reconfigure_hardware and not args.coin_interface:
        hardware_settings = {}
        hardware_summary = {"interface": existing_interface, "host": {}}
        print(f"\n[Hardware] Existing {existing_interface} configuration preserved. Use --reconfigure-hardware to change it.")
    else:
        stopped_for_reconfigure = bool(existing_env and args.reconfigure_hardware and args.write_system_configs)
        if stopped_for_reconfigure:
            subprocess.run(["systemctl", "stop", "pisowifi-coin", "pisowifi-backend"], check=False)
        try:
            hardware_settings, hardware_summary = run_hardware_wizard(
                args.non_interactive,
                args.skip_hardware_test,
                args.coin_interface,
            )
        except Exception as exc:
            if stopped_for_reconfigure:
                subprocess.run(["systemctl", "start", "pisowifi-backend", "pisowifi-coin"], check=False)
            print(f"[Error] Hardware configuration stopped: {exc}")
            sys.exit(1)

    print("\nSummary of Configuration:")
    print(f" - Installation Base Dir: {args.base_dir}")
    print(f" - WAN Network Interface: {args.wan_interface}")
    print(f" - LAN Network Interface: {args.lan_interface}")
    print(f" - Captive Gateway IP:    {args.gateway_ip}")
    print(f" - Captive Local Subnet:  {subnet_cidr}")
    print(f" - DHCP IP Range:         {args.dhcp_start} - {args.dhcp_end}")
    print(f" - Backend Port:          {args.backend_port}")
    print(f" - Captive Web Port:      {args.captive_portal_port}")
    print(f" - Coin Interface:        {hardware_settings.get('COIN_INTERFACE', existing_interface or 'arduino')}")
    print("==================================================")

    import secrets
    import bcrypt
    jwt_secret = secrets.token_hex(32) # 256 bits for RFC 7518 compliance
    initial_admin_pw = secrets.token_urlsafe(16)
    fresh_admin_hash = bcrypt.hashpw(initial_admin_pw.encode(), bcrypt.gensalt(12)).decode("utf-8")
    generated_db_pw = secrets.token_urlsafe(24)

    env_updates = {
        "PISOWIFI_BASE_DIR": args.base_dir,
        "PISOWIFI_RUN_DIR": f"{args.base_dir}/run",
        "SFX_DIRECTORY": f"{args.base_dir}/sfx",
        "PISOWIFI_GATEWAY_IP": args.gateway_ip,
        "PISOWIFI_SUBNET_CIDR": subnet_cidr,
        "PISOWIFI_LAN_INTERFACE_FALLBACK": args.lan_interface,
        "PISOWIFI_DATABASE_TYPE": existing_env.get("PISOWIFI_DATABASE_TYPE", "mysql"),
        "DATABASE_HOST": existing_env.get("DATABASE_HOST", "localhost"),
        "DATABASE_PORT": existing_env.get("DATABASE_PORT", "3306"),
        "DATABASE_USER": existing_env.get("DATABASE_USER", "pisowifi"),
        "DATABASE_PASSWORD": existing_env.get("DATABASE_PASSWORD", generated_db_pw),
        "DATABASE_NAME": existing_env.get("DATABASE_NAME", "pisowifi"),
        "SERIAL_PORT": args.serial_port,
        "PISOWIFI_BACKEND_PORT": str(args.backend_port),
        "CAPTIVE_PORTAL_PORT": str(args.captive_portal_port),
        "ADMIN_USERNAME": existing_env.get("ADMIN_USERNAME", "admin"),
        "ADMIN_PASSWORD_HASH": existing_env.get("ADMIN_PASSWORD_HASH", f"'{fresh_admin_hash}'"),
        "ADMIN_JWT_SECRET": existing_env.get("ADMIN_JWT_SECRET", jwt_secret),
        **hardware_settings,
    }
    if not existing_env.get("ADMIN_PASSWORD_HASH"):
        print(f"\n[SECURITY] Generated Fresh Admin Credentials:")
        print(f" - Username: admin")
        print(f" - Password: {initial_admin_pw}")
        print(" [NOTE: Change this password immediately after logging in]")
    env_content = build_env_content(existing_env, env_updates)

    rollback_mgr = RollbackManager()

    try:
        deploy_application(SOURCE_DIR, args.base_dir, args.dry_run)

        # A: Generate local environment file
        env_file = os.path.join(args.base_dir, "backend", ".env")
        if args.dry_run:
            print(f"\n[DRY-RUN] Would write environment file to: {env_file}")
            print(f"[DRY-RUN] Environment keys: {', '.join(sorted(env_updates))} (secrets redacted)")
        else:
            if args.inject_failure_step == "env":
                raise RuntimeError("Injected failure during environment file creation.")
            rollback_mgr.write_file(env_file, env_content)
            os.chmod(env_file, 0o600)
            print(f"\n[OK] Environment variables written to: {env_file}")

        # B: Compile Templates
        config_dir = os.path.join(args.base_dir, "config")
        params = {
            "base_dir": args.base_dir,
            "backend_port": args.backend_port,
            "captive_portal_port": args.captive_portal_port,
            "gateway_ip": args.gateway_ip,
            "lan_interface": args.lan_interface,
            "wan_interface": args.wan_interface,
            "dhcp_start": args.dhcp_start,
            "dhcp_end": args.dhcp_end,
            "nft_table_name": "pisowifi",
            "nft_set_name": "authenticated_clients",
            "gateway_prefix": gateway_prefix,
        }

        if args.inject_failure_step == "render":
            raise RuntimeError("Injected failure during template generation.")

        if args.dry_run:
            print(f"\n[DRY-RUN] Would render templates under: {config_dir}")
        else:
            output_paths = render_templates(config_dir, params)

        # C: System installs
        if args.write_system_configs:
            if args.inject_failure_step == "system_files":
                raise RuntimeError("Injected failure during system config writes.")

            if args.dry_run:
                print("\n[DRY-RUN] Would copy rendered system configs to: /etc system folders")
                print("[DRY-RUN] Would reload systemd services")
            else:
                print("\nWriting configurations to system directories...")
                install_system_files(output_paths, rollback_mgr=rollback_mgr)

                # Install CLI binary
                cli_src = os.path.join(args.base_dir, "bin", "pisowifi")
                cli_dst = "/usr/local/bin/pisowifi"
                if os.path.exists(cli_src):
                    print("Installing PisoWiFi CLI manager to /usr/local/bin/pisowifi...")
                    os.chmod(cli_src, 0o755)
                    rollback_mgr.create_symlink(cli_src, cli_dst)

                # Validate and explicitly reload services that apt may already
                # have started with their distribution-default configuration.
                print("Validating configuration and restarting services...")
                install_application_dependencies(args.base_dir, args.dry_run)
                setup_database(args.base_dir, args.dry_run)
                activate_system_services()
                print("[OK] Deployment configuration installed and services restarted successfully!")

                if hardware_summary.get("interface") == "gpio":
                    print_completion_hardware(
                        hardware_summary,
                        env_file,
                        "/opt/pisowifi/logs/install.log",
                    )
        else:
            if not args.dry_run:
                print("\nTo apply these configurations to your system, run as root:")
                print("  sudo python3 install.py --non-interactive --write-system-configs")

    except Exception as exc:
        logger.error(f"\n[INSTALLATION FAILED] Error: {exc}")
        if not args.dry_run:
            rollback_logger = get_logger("rollback", "rollback.log")
            rollback_logger.error(f"Installation failed. Starting rollback due to error: {exc}")
            rollback_mgr.rollback()
            rollback_logger.info("Rollback completed successfully.")
        if stopped_for_reconfigure:
            subprocess.run(["systemctl", "start", "pisowifi-backend", "pisowifi-coin"], check=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
