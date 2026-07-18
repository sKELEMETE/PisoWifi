import os
import sys
import subprocess
import shutil
from installer.utils import check_root, get_version
from installer.backup import create_and_validate_backup
from installer.rollback import RollbackManager
from installer.templates import render_templates, install_system_files
from installer.doctor import DoctorCheck
from installer.log_manager import get_logger

logger = get_logger("upgrade", "upgrade.log")


def migrate_env(base_dir: str) -> None:
    """
    Migrates old environment parameters into the new .env format,
    preserving customizations and adding defaults.
    """
    root_env = "/opt/pisowifi/.env"
    backend_env = os.path.join(base_dir, "backend", ".env")

    import secrets
    # Defaults defined in config
    defaults = {
        "SERIAL_PORT": "AUTO",
        "SERIAL_BAUDRATE": "9600",
        "SERIAL_TIMEOUT": "1",
        "SERIAL_RECONNECT_INTERVAL": "5",
        "SERIAL_DEBOUNCE_MS": "250",
        "PISOWIFI_DATABASE_TYPE": "mysql",
        "PISOWIFI_BACKEND_PORT": "8000",
        "CAPTIVE_PORTAL_PORT": "80",
        "PISOWIFI_GATEWAY_IP": "10.0.0.1",
        "PISOWIFI_SUBNET_CIDR": "10.0.0.0/24",
        "PISOWIFI_LAN_INTERFACE_FALLBACK": "enxc817f552a5c6",
        "ADMIN_JWT_SECRET": secrets.token_hex(16),
    }

    for path in [root_env, backend_env]:
        if not os.path.exists(path):
            continue

        current = {}
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    current[k.strip()] = v.strip()

        # Apply defaults
        for k, v in defaults.items():
            if k not in current:
                current[k] = v

        # Write back
        with open(path, "w") as f:
            f.write("# PisoWiFi Environment Settings\n")
            for k, v in sorted(current.items()):
                f.write(f"{k}={v}\n")
    logger.info("Environment configuration migrated successfully.")


def run_upgrade(base_dir: str) -> bool:
    if not check_root():
        logger.error("You must run as root to perform upgrade.")
        return False

    logger.info("\n==================================================")
    logger.info("            PISOWIFI UPGRADE WORKFLOW             ")
    logger.info("==================================================")

    rollback_mgr = RollbackManager()

    try:
        # 1. Pre-upgrade backup
        logger.info("Step 1: Creating configuration validation backup...")
        backup_dir = os.path.join(base_dir, "backups")
        backup_path = create_and_validate_backup(base_dir, backup_dir)
        logger.info(f"Backup successfully archived to: {backup_path}")

        # 2. Configuration migration
        logger.info("Step 2: Migrating environment configurations...")
        migrate_env(base_dir)

        # 3. Regenerate dynamic templates
        logger.info("Step 3: Regenerating configuration templates...")
        sys.path.insert(0, os.path.join(base_dir, "backend"))
        import config

        # Extract existing dhcp range settings from config templates or live settings if possible
        dhcp_start = "10.0.0.20"
        dhcp_end = "10.0.0.254"
        for conf_path in ["/etc/dnsmasq.d/pisowifi.conf", os.path.join(base_dir, "config", "dnsmasq", "dnsmasq.conf")]:
            if os.path.exists(conf_path):
                try:
                    with open(conf_path, "r") as f:
                        for line in f:
                            if line.strip().startswith("dhcp-range="):
                                parts = line.strip().split("=")[1].split(",")
                                if len(parts) >= 2:
                                    dhcp_start = parts[0].strip()
                                    dhcp_end = parts[1].strip()
                                    break
                except Exception:
                    pass

        # Extract WAN interface
        wan_interface = None
        for conf_path in ["/etc/nftables.conf", os.path.join(base_dir, "config", "nftables", "nftables.conf")]:
            if os.path.exists(conf_path):
                try:
                    with open(conf_path, "r") as f:
                        for line in f:
                            if "oifname" in line and "masquerade" in line:
                                parts = line.strip().split("oifname")
                                if len(parts) >= 2:
                                    iface = parts[1].split()[0].strip('"').strip("'")
                                    if iface:
                                        wan_interface = iface
                                        break
                except Exception:
                    pass

        if not wan_interface:
            try:
                with open("/proc/net/route") as f:
                    for line in f.readlines()[1:]:
                        parts = line.split()
                        if len(parts) >= 4 and parts[1] == "00000000" and parts[3] == "0002":
                            wan_interface = parts[0]
                            break
            except Exception:
                pass

        if not wan_interface:
            wan_interface = "eth0"

        nft_table_name = getattr(config, "NFT_TABLE_NAME", "pisowifi")
        nft_set_name = getattr(config, "NFT_SET_NAME", "authenticated_clients")

        params = {
            "base_dir": base_dir,
            "gateway_ip": config.GATEWAY_IP,
            "subnet_cidr": config.SUBNET_CIDR,
            "lan_interface": config.LAN_INTERFACE_FALLBACK,
            "wan_interface": wan_interface,
            "dhcp_start": dhcp_start,
            "dhcp_end": dhcp_end,
            "nft_table_name": nft_table_name,
            "nft_set_name": nft_set_name,
            "backend_port": config.BACKEND_PORT,
            "captive_portal_port": config.CAPTIVE_PORTAL_PORT,
            "path_nft": config.PATH_NFT,
            "path_tc": config.PATH_TC,
            "path_ip": config.PATH_IP,
            "path_modprobe": config.PATH_MODPROBE,
        }

        output_paths = render_templates(os.path.join(base_dir, "config"), params)
        install_system_files(output_paths, rollback_mgr=rollback_mgr)

        # 4. Database Migrations
        logger.info("Step 4: Applying database schema migrations (Alembic)...")
        # Run programmatic Alembic migrations
        from alembic.config import Config
        from alembic import command

        alembic_ini_path = os.path.join(base_dir, "backend", "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied.")

        # 5. Reload systemd & Restart services
        logger.info("Step 5: Restarting system services...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "restart", "pisowifi-backend", "pisowifi-coin"], check=True)
        logger.info("Services restarted successfully.")

        # 6. Post-Upgrade Validation
        logger.info("Step 6: Executing post-upgrade health checks...")
        doctor = DoctorCheck()
        is_healthy = doctor.run_all()

        if not is_healthy:
            raise RuntimeError("Post-upgrade health checks failed. Triggering automatic rollback...")

        logger.info("==================================================")
        logger.info("[OK] PisoWiFi upgraded successfully!")
        return True

    except Exception as exc:
        logger.error(f"Upgrade failed: {exc}")
        logger.error("Initiating automatic rollback of all system files...")
        rollback_mgr.rollback()
        logger.info("System files rollback complete. Restarting previous version services...")
        try:
            subprocess.run(["systemctl", "daemon-reload"], check=False)
            subprocess.run(["systemctl", "restart", "pisowifi-backend", "pisowifi-coin"], check=False)
        except Exception:
            pass
        return False
