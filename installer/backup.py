import os
import tarfile
import time


def create_and_validate_backup(base_dir: str, backup_dest_dir: str) -> str:
    """
    Creates a backup of configuration files (.env, sfx, config templates) and validation checks it.
    Returns the backup archive path. Raises exception if backup fails or is invalid.
    """
    os.makedirs(backup_dest_dir, exist_ok=True)
    timestamp = int(time.time())
    backup_file = os.path.join(backup_dest_dir, f"pisowifi_backup_{timestamp}.tar.gz")

    target_files = []

    env_path = os.path.join(base_dir, "backend", ".env")
    if os.path.exists(env_path):
        target_files.append((env_path, "backend/.env"))

    sqlite_path = os.path.join(base_dir, "pisowifi.db")
    if os.path.exists(sqlite_path):
        target_files.append((sqlite_path, "pisowifi.db"))

    config_dir = os.path.join(base_dir, "config")
    if os.path.exists(config_dir):
        target_files.append((config_dir, "config"))

    # System configs
    system_configs = [
        ("/etc/systemd/system/pisowifi-backend.service", "etc/pisowifi-backend.service"),
        ("/etc/systemd/system/pisowifi-coin.service", "etc/pisowifi-coin.service"),
        ("/etc/systemd/system/pisowifi-network.service", "etc/pisowifi-network.service"),
        ("/etc/nginx/sites-available/pisowifi", "etc/nginx-pisowifi"),
        ("/etc/dnsmasq.d/pisowifi.conf", "etc/dnsmasq-pisowifi.conf"),
        ("/etc/nftables.conf", "etc/nftables.conf"),
    ]
    for path, arcname in system_configs:
        if os.path.exists(path):
            target_files.append((path, arcname))

    if not target_files:
        print("[Backup] No existing configuration files found to backup.")
        return ""

    print(f"[Backup] Creating backup archive at {backup_file}...")
    try:
        with tarfile.open(backup_file, "w:gz") as tar:
            for path, arcname in target_files:
                tar.add(path, arcname=arcname)
        os.chmod(backup_file, 0o600)
    except Exception as e:
        raise RuntimeError(f"Backup archiving failed: {e}")

    # Validation check: verify archive is readable and not empty
    print("[Backup] Validating backup archive integrity...")
    try:
        if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
            raise RuntimeError("Backup file is empty or missing.")

        with tarfile.open(backup_file, "r:gz") as tar:
            members = tar.getnames()
            if not members:
                raise RuntimeError("Backup archive contains no files.")
            print(f"[Backup] Integrity validation successful! Included files: {', '.join(members)}")
    except Exception as e:
        if os.path.exists(backup_file):
            os.remove(backup_file)
        raise RuntimeError(f"Backup validation failed: {e}")

    return backup_file
