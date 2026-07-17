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

logger = get_logger("install", "install.log")


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
    parser.add_argument("--write-system-configs", action="store_true", help="Write compiled configs directly to /etc")
    parser.add_argument("--skip-system-checks", action="store_true", help="Skip OS compatibility and kernel capability checks")
    
    # Phase 2 CLI options
    parser.add_argument("--dry-run", action="store_true", help="Perform checks and config generation, but do not write any files")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall PisoWiFi services and configurations")
    parser.add_argument("--preserve-data", action="store_true", default=True, help="Preserve database/logs during uninstall")
    parser.add_argument("--purge", action="store_false", dest="preserve_data", help="Purge all user database records and configurations during uninstall")
    parser.add_argument("--inject-failure-step", type=str, help="For testing: inject failure at a specific install step ('env', 'render', 'system_files')")

    args = parser.parse_args()

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
            args.backend_port = int(backend_port)
        portal_port = input(f"Nginx Web Port [{args.captive_portal_port}]: ").strip()
        if portal_port:
            args.captive_portal_port = int(portal_port)

        serial_port = input(f"Serial port for Coin Acceptor [{args.serial_port}]: ").strip()
        if serial_port:
            args.serial_port = serial_port
    else:
        if not args.lan_interface:
            args.lan_interface = detected_lan or "eth1"
        if not args.wan_interface:
            args.wan_interface = detected_wan or "eth0"

    try:
        net = ipaddress.IPv4Network(f"{args.gateway_ip}/{args.subnet_mask}", strict=False)
        subnet_cidr = str(net)
    except Exception:
        subnet_cidr = f"{args.gateway_ip}/24"

    print("\nSummary of Configuration:")
    print(f" - Installation Base Dir: {args.base_dir}")
    print(f" - WAN Network Interface: {args.wan_interface}")
    print(f" - LAN Network Interface: {args.lan_interface}")
    print(f" - Captive Gateway IP:    {args.gateway_ip}")
    print(f" - Captive Local Subnet:  {subnet_cidr}")
    print(f" - DHCP IP Range:         {args.dhcp_start} - {args.dhcp_end}")
    print(f" - Backend Port:          {args.backend_port}")
    print(f" - Captive Web Port:      {args.captive_portal_port}")
    print(f" - Hardware Serial Port:  {args.serial_port}")
    print("==================================================")

    # 1. Generate local environment content (include default admin credentials)
    env_content = f"""# PisoWiFi Environment Settings
PISOWIFI_BASE_DIR={args.base_dir}
PISOWIFI_RUN_DIR={args.base_dir}/run
SFX_DIRECTORY={args.base_dir}/sfx
PISOWIFI_GATEWAY_IP={args.gateway_ip}
PISOWIFI_SUBNET_CIDR={subnet_cidr}
PISOWIFI_LAN_INTERFACE_FALLBACK={args.lan_interface}
SERIAL_PORT={args.serial_port}
PISOWIFI_BACKEND_PORT={args.backend_port}
CAPTIVE_PORTAL_PORT={args.captive_portal_port}

# Admin Credentials Hardening
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
"""

    rollback_mgr = RollbackManager()

    try:
        # A: Generate local environment file
        env_file = os.path.join(args.base_dir, "backend", ".env")
        if args.dry_run:
            print(f"\n[DRY-RUN] Would write environment file to: {env_file}")
            print(f"--- CONTENT ---\n{env_content}---------------")
        else:
            if args.inject_failure_step == "env":
                raise RuntimeError("Injected failure during environment file creation.")
            rollback_mgr.write_file(env_file, env_content)
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
                    rollback_mgr.copy_file(cli_src, cli_dst)
                    os.chmod(cli_dst, 0o755)

                # Reload systemd and restart backend services
                print("Reloading systemd daemons...")
                subprocess.run(["systemctl", "daemon-reload"], check=False)
                print("Restarting systemd backend services...")
                subprocess.run(["systemctl", "restart", "pisowifi-backend"], check=False)
                subprocess.run(["systemctl", "restart", "pisowifi-coin"], check=False)
                print("[OK] Deployment configuration installed and services restarted successfully!")
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
        sys.exit(1)


if __name__ == "__main__":
    main()
