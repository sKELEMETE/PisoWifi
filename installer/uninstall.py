import os
import shutil
import subprocess
from installer.utils import check_root


def run_uninstall(base_dir: str, preserve_data: bool = True) -> None:
    """
    Stops services, removes system files, and deletes configuration files.
    Optionally preserves database and log files.
    """
    if not check_root():
        print("[Error] You must run as root to uninstall PisoWiFi.")
        return

    print("==================================================")
    print("           PISOWIFI UNINSTALL PROCESS             ")
    print("==================================================")

    # 1. Stop and disable services
    services = ["pisowifi-backend", "pisowifi-coin", "pisowifi-network"]
    for service in services:
        print(f"Stopping service {service}...")
        subprocess.run(["systemctl", "stop", service], check=False)
        print(f"Disabling service {service}...")
        subprocess.run(["systemctl", "disable", service], check=False)

        # Remove systemd files
        service_path = f"/etc/systemd/system/{service}.service"
        if os.path.exists(service_path):
            os.remove(service_path)
            print(f"Removed systemd unit: {service_path}")

    # Reload systemd
    subprocess.run(["systemctl", "daemon-reload"], check=False)

    # 2. Remove Nginx site
    nginx_avail = "/etc/nginx/sites-available/pisowifi"
    nginx_enabled = "/etc/nginx/sites-enabled/pisowifi"
    if os.path.exists(nginx_enabled) or os.path.islink(nginx_enabled):
        try:
            os.remove(nginx_enabled)
            print(f"Removed Nginx site link: {nginx_enabled}")
        except Exception as e:
            print(f"Failed to remove link {nginx_enabled}: {e}")
    if os.path.exists(nginx_avail):
        os.remove(nginx_avail)
        print(f"Removed Nginx configuration: {nginx_avail}")
    nginx_default = "/etc/nginx/sites-available/default"
    nginx_default_link = "/etc/nginx/sites-enabled/default"
    if os.path.exists(nginx_default) and not os.path.exists(nginx_default_link):
        os.symlink(nginx_default, nginx_default_link)
        print("Restored default Nginx site link.")

    # 3. Remove Dnsmasq config
    dnsmasq_conf = "/etc/dnsmasq.d/pisowifi.conf"
    if os.path.exists(dnsmasq_conf):
        os.remove(dnsmasq_conf)
        print(f"Removed Dnsmasq configuration: {dnsmasq_conf}")

    # 4. Revert Nftables config if backup exists
    nft_conf = "/etc/nftables.conf"
    nft_orig = "/etc/nftables.conf.orig"
    if os.path.exists(nft_orig):
        shutil.move(nft_orig, nft_conf)
        print("Restored original Nftables configuration.")
    elif os.path.exists(nft_conf):
        # We can clean the file or do nothing
        pass

    # Restart networking/Nginx services to clean port bindings
    print("Restarting Nginx and Dnsmasq to refresh configs...")
    subprocess.run(["systemctl", "restart", "nginx"], check=False)
    subprocess.run(["systemctl", "restart", "dnsmasq"], check=False)

    # 5. Remove base directories
    if not preserve_data:
        print(f"Removing runtime files and logs under {base_dir}...")
        for folder in ["config", "run", "uploads"]:
            path = os.path.join(base_dir, folder)
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"Removed folder: {path}")

        # Remove backend env
        env_file = os.path.join(base_dir, "backend", ".env")
        if os.path.exists(env_file):
            os.remove(env_file)
            print(f"Removed: {env_file}")

        # Delete local SQLite db if exists
        sqlite_db = os.path.join(base_dir, "pisowifi.db")
        if os.path.exists(sqlite_db):
            os.remove(sqlite_db)
            print(f"Deleted local SQLite database: {sqlite_db}")
    else:
        print("\nPreserving database records, logs, and branding assets.")

    print("\n[OK] PisoWiFi has been successfully uninstalled.")
