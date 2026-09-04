import os
import shutil
import subprocess
import tempfile


def ensure_admin_tls_certificate(
    base_dir: str,
    gateway_ip: str,
    rollback_mgr=None,
    dry_run: bool = False,
) -> tuple[str, str]:
    """Create the local admin TLS certificate when an installation has none."""
    cert_dir = os.path.join(base_dir, "config", "nginx")
    cert_path = os.path.join(cert_dir, "admin.crt")
    key_path = os.path.join(cert_dir, "admin.key")

    if os.path.isfile(cert_path) and os.path.isfile(key_path):
        if not dry_run:
            os.chmod(cert_path, 0o644)
            os.chmod(key_path, 0o600)
        return cert_path, key_path

    if dry_run:
        print(f"[DRY-RUN] Would generate admin TLS certificate: {cert_path}")
        return cert_path, key_path

    os.makedirs(cert_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pisowifi-tls-") as temp_dir:
        temp_cert = os.path.join(temp_dir, "admin.crt")
        temp_key = os.path.join(temp_dir, "admin.key")
        subprocess.run(
            [
                "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
                "-keyout", temp_key,
                "-out", temp_cert,
                "-days", "825",
                "-subj", f"/CN={gateway_ip}",
                "-addext", f"subjectAltName=IP:{gateway_ip}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        for source, destination in ((temp_cert, cert_path), (temp_key, key_path)):
            if rollback_mgr:
                with open(source) as stream:
                    rollback_mgr.write_file(destination, stream.read())
            else:
                shutil.copy2(source, destination)

    os.chmod(cert_path, 0o644)
    os.chmod(key_path, 0o600)
    print(f"[OK] Generated admin TLS certificate: {cert_path}")
    return cert_path, key_path


def render_templates(config_dir: str, params: dict) -> dict[str, str]:
    templates = {
        "systemd/pisowifi-backend.service": os.path.join(config_dir, "systemd", "pisowifi-backend.service.template"),
        "systemd/pisowifi-coin.service": os.path.join(config_dir, "systemd", "pisowifi-coin.service.template"),
        "systemd/pisowifi-network.service": os.path.join(config_dir, "systemd", "pisowifi-network.service.template"),
        "nginx/pisowifi.conf": os.path.join(config_dir, "nginx", "pisowifi.conf.template"),
        "dnsmasq/dnsmasq.conf": os.path.join(config_dir, "dnsmasq", "dnsmasq.conf.template"),
        "nftables/nftables.conf": os.path.join(config_dir, "nftables", "nftables.conf.template"),
    }

    output_paths = {}
    for name, template_path in templates.items():
        if not os.path.exists(template_path):
            print(f"[Warning] Template file not found: {template_path}. Skipping.")
            continue

        with open(template_path, "r") as f:
            template_text = f.read()

        rendered_text = template_text
        for key, val in params.items():
            rendered_text = rendered_text.replace(f"{{{key}}}", str(val))

        output_file = os.path.join(config_dir, name)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            f.write(rendered_text)
        print(f"[OK] Generated: {output_file}")
        output_paths[name] = output_file

    return output_paths


import hashlib
import json

HASH_FILE = "/opt/pisowifi/config/.hashes.json"


def calculate_hash(filepath: str) -> str:
    if not os.path.exists(filepath):
        return ""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_hashes() -> dict:
    if os.path.exists(HASH_FILE):
        try:
            with open(HASH_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_hashes(hashes: dict) -> None:
    os.makedirs(os.path.dirname(HASH_FILE), exist_ok=True)
    try:
        with open(HASH_FILE, "w") as f:
            json.dump(hashes, f, indent=4)
    except Exception:
        pass


def install_system_files(output_paths: dict[str, str], rollback_mgr=None) -> None:
    stored_hashes = load_hashes()
    new_hashes = {}

    install_targets = {
        "systemd/pisowifi-backend.service": "/etc/systemd/system/pisowifi-backend.service",
        "systemd/pisowifi-coin.service": "/etc/systemd/system/pisowifi-coin.service",
        "systemd/pisowifi-network.service": "/etc/systemd/system/pisowifi-network.service",
        "nginx/pisowifi.conf": "/etc/nginx/sites-available/pisowifi",
        "dnsmasq/dnsmasq.conf": "/etc/dnsmasq.d/pisowifi.conf",
        "nftables/nftables.conf": "/etc/nftables.conf",
    }

    for key, dst in install_targets.items():
        src = output_paths.get(key)
        if not src:
            continue

        # Detect custom modification
        if os.path.exists(dst):
            current_hash = calculate_hash(dst)
            previous_hash = stored_hashes.get(dst)
            if previous_hash and current_hash != previous_hash:
                backup_dst = dst + ".custom"
                print(f"[WARNING] Custom edits detected on {dst}! Saving backup to {backup_dst}")
                try:
                    shutil.copy(dst, backup_dst)
                except Exception as exc:
                    print(f" -> Backup failed: {exc}")

        # Perform install
        if dst == "/etc/nftables.conf":
            if os.path.exists(dst) and not os.path.exists(dst + ".orig"):
                try:
                    shutil.copy(dst, dst + ".orig")
                except Exception:
                    pass

        if rollback_mgr:
            rollback_mgr.copy_file(src, dst)
        else:
            shutil.copy(src, dst)

        print(f" -> Installed: {dst}")

        # Link Nginx site
        if key == "nginx/pisowifi.conf":
            default_site = "/etc/nginx/sites-enabled/default"
            if os.path.exists(default_site) or os.path.islink(default_site):
                if rollback_mgr:
                    rollback_mgr.remove_path(default_site)
                else:
                    os.remove(default_site)
            dst_nginx_enable = "/etc/nginx/sites-enabled/pisowifi"
            if not os.path.exists(dst_nginx_enable):
                try:
                    if rollback_mgr:
                        rollback_mgr.create_symlink(dst, dst_nginx_enable)
                    else:
                        os.symlink(dst, dst_nginx_enable)
                    print(f" -> Enabled site link: {dst_nginx_enable}")
                except Exception as exc:
                    print(f" -> Link failed: {exc}")

        # Record new hash
        new_hashes[dst] = calculate_hash(dst)

    save_hashes(new_hashes)
