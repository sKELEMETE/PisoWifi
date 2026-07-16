import os
import shutil


def render_templates(config_dir: str, params: dict) -> dict[str, str]:
    templates = {
        "systemd/pisowifi-backend.service": os.path.join(config_dir, "systemd", "pisowifi-backend.service.template"),
        "systemd/pisowifi-coin.service": os.path.join(config_dir, "systemd", "pisowifi-coin.service.template"),
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


def install_system_files(output_paths: dict[str, str], rollback_mgr=None) -> None:
    # Systemd
    for service in ["pisowifi-backend.service", "pisowifi-coin.service"]:
        src = output_paths.get(f"systemd/{service}")
        if src:
            dst = f"/etc/systemd/system/{service}"
            if rollback_mgr:
                rollback_mgr.copy_file(src, dst)
            else:
                shutil.copy(src, dst)
            print(f" -> Installed systemd service to: {dst}")

    # Nginx
    src_nginx = output_paths.get("nginx/pisowifi.conf")
    if src_nginx:
        dst_nginx_avail = "/etc/nginx/sites-available/pisowifi"
        dst_nginx_enable = "/etc/nginx/sites-enabled/pisowifi"
        if rollback_mgr:
            rollback_mgr.copy_file(src_nginx, dst_nginx_avail)
        else:
            shutil.copy(src_nginx, dst_nginx_avail)
        print(f" -> Installed Nginx configuration to: {dst_nginx_avail}")
        if not os.path.exists(dst_nginx_enable):
            try:
                if rollback_mgr:
                    rollback_mgr.create_symlink(dst_nginx_avail, dst_nginx_enable)
                else:
                    os.symlink(dst_nginx_avail, dst_nginx_enable)
                print(f" -> Enabled site link: {dst_nginx_enable}")
            except Exception as exc:
                print(f" -> Link failed: {exc}")

    # Dnsmasq
    src_dnsmasq = output_paths.get("dnsmasq/dnsmasq.conf")
    if src_dnsmasq:
        dst_dnsmasq = "/etc/dnsmasq.d/pisowifi.conf"
        if rollback_mgr:
            rollback_mgr.copy_file(src_dnsmasq, dst_dnsmasq)
        else:
            shutil.copy(src_dnsmasq, dst_dnsmasq)
        print(f" -> Installed Dnsmasq configuration to: {dst_dnsmasq}")

    # Nftables
    src_nft = output_paths.get("nftables/nftables.conf")
    if src_nft:
        dst_nft = "/etc/nftables.conf"
        if os.path.exists(dst_nft) and not os.path.exists(dst_nft + ".orig"):
            shutil.copy(dst_nft, dst_nft + ".orig")
        if rollback_mgr:
            rollback_mgr.copy_file(src_nft, dst_nft)
        else:
            shutil.copy(src_nft, dst_nft)
        print(f" -> Installed Nftables configuration to: {dst_nft}")
