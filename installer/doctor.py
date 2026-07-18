import os
import sys
import shutil
import subprocess
import socket
import httpx
from installer.log_manager import get_logger

logger = get_logger("doctor", "doctor.log")


class DoctorCheck:

    def __init__(self):
        self.critical_failures = 0
        self.warnings = 0

    def run_check(self, name: str, check_func, is_critical=True):
        try:
            status, msg = check_func()
            if status == "healthy":
                logger.info(f"[HEALTHY] {name}: {msg}")
            elif status == "warning":
                self.warnings += 1
                logger.info(f"[WARNING] {name}: {msg}")
            else:
                if is_critical:
                    self.critical_failures += 1
                    logger.info(f"[CRITICAL] {name}: {msg}")
                else:
                    self.warnings += 1
                    logger.info(f"[WARNING] {name}: {msg}")
        except Exception as exc:
            if is_critical:
                self.critical_failures += 1
                logger.info(f"[CRITICAL] {name}: Exception occurred: {exc}")
            else:
                self.warnings += 1
                logger.info(f"[WARNING] {name}: Exception occurred: {exc}")

    def run_all(self) -> bool:
        logger.info("\n==================================================")
        logger.info("             PISOWIFI SYSTEM DOCTOR               ")
        logger.info("==================================================")

        # 1. Check database connectivity
        self.run_check("Database Connection", self.check_database, is_critical=True)
        # 2. Check Backend API
        self.run_check("Backend API Services", self.check_backend, is_critical=True)
        # 3. Check Network Interfaces
        self.run_check("Network Interfaces", self.check_interfaces, is_critical=True)
        # 4. Check Kernel Modules
        self.run_check("Kernel Modules", self.check_kernel_modules, is_critical=False)
        # 5. Check System Services
        self.run_check("System Services", self.check_system_services, is_critical=False)
        # 6. Check Firewall config
        self.run_check("Firewall Configuration", self.check_firewall, is_critical=True)
        # 7. Check Bandwidth control
        self.run_check("Traffic Control (tc)", self.check_bandwidth, is_critical=False)
        # 8. Check Serial Acceptor Connection
        self.run_check("Hardware Serial Connection", self.check_serial, is_critical=False)
        # 9. Check Templates and Generated configs
        self.run_check("Configuration Templates", self.check_templates, is_critical=True)
        # 10. Check File Permissions
        self.run_check("Runtime File Permissions", self.check_permissions, is_critical=True)
        # 11. Check Internet Access
        self.run_check("Internet Access Validation", self.check_internet, is_critical=False)

        logger.info("==================================================")
        logger.info(f"Doctor Summary: {self.critical_failures} Critical failures, {self.warnings} Warnings.")
        if self.critical_failures > 0:
            logger.info("Status: CRITICAL (Issues must be addressed for operation)")
            return False
        elif self.warnings > 0:
            logger.info("Status: WARNING (Minor issues detected, but functional)")
            return True
        else:
            logger.info("Status: HEALTHY (All checks passed!)")
            return True

    def check_database(self) -> tuple[str, str]:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
        try:
            import config as app_config
            from sqlalchemy import create_engine, text
            engine = create_engine(app_config.DATABASE_URL, connect_args={"connect_timeout": 3} if "sqlite" not in app_config.DATABASE_URL else {})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return "healthy", f"Connected successfully via {app_config.DATABASE_TYPE} engine."
        except Exception as e:
            return "critical", f"Database connection failed: {e}"

    def check_backend(self) -> tuple[str, str]:
        try:
            import config as app_config
            port = app_config.BACKEND_PORT
            res = httpx.get(f"http://127.0.0.1:{port}/api/v1/health", timeout=2.0)
            if res.status_code == 200:
                return "healthy", f"Backend API is responsive on port {port}."
            return "critical", f"Backend API returned status code {res.status_code}."
        except Exception as e:
            return "critical", f"Backend API not responsive: {e}"

    def check_interfaces(self) -> tuple[str, str]:
        import config as app_config
        lan = app_config.LAN_INTERFACE_FALLBACK
        if not os.path.exists(f"/sys/class/net/{lan}"):
            return "critical", f"Configured LAN interface '{lan}' does not exist."

        try:
            with open(f"/sys/class/net/{lan}/operstate") as f:
                state = f.read().strip()
            if state in ["up", "unknown"]:
                return "healthy", f"Interface '{lan}' exists and is {state}."
            return "warning", f"Interface '{lan}' exists but operstate is '{state}'."
        except Exception as e:
            return "warning", f"Interface '{lan}' exists but operstate check failed: {e}"

    def check_kernel_modules(self) -> tuple[str, str]:
        missing = []
        for mod in ["sch_htb", "ifb"]:
            if not os.path.exists(f"/sys/module/{mod}"):
                missing.append(mod)
        if missing:
            return "warning", f"Missing kernel modules: {', '.join(missing)}."
        return "healthy", "Core queuing/shaping kernel modules are loaded."

    def check_system_services(self) -> tuple[str, str]:
        services = ["nginx", "dnsmasq", "hostapd"]
        inactive = []
        systemctl_path = shutil.which("systemctl") or "/usr/bin/systemctl"
        for s in services:
            res = subprocess.run([systemctl_path, "is-active", s], capture_output=True, text=True)
            if res.stdout.strip() != "active":
                inactive.append(s)
        if inactive:
            return "warning", f"System services inactive: {', '.join(inactive)}. Captive portal functionality might be offline."
        return "healthy", "Nginx, Dnsmasq, and Hostapd system services are active."

    def check_firewall(self) -> tuple[str, str]:
        nft_path = shutil.which("nft")
        if not nft_path:
            return "critical", "nftables command utility is not installed."

        try:
            res = subprocess.run([nft_path, "list", "table", "inet", "pisowifi"], capture_output=True, text=True)
            if res.returncode == 0:
                return "healthy", "Nftables firewall tables successfully active."
            return "critical", "PisoWiFi nftables table rules are not loaded."
        except Exception as e:
            return "critical", f"Failed to execute nft commands: {e}"

    def check_bandwidth(self) -> tuple[str, str]:
        tc_path = shutil.which("tc")
        if not tc_path:
            return "warning", "tc command utility is not installed. Bandwidth limiting will fail."

        import config as app_config
        lan = app_config.LAN_INTERFACE_FALLBACK
        try:
            res = subprocess.run([tc_path, "qdisc", "show", "dev", lan], capture_output=True, text=True)
            if "htb" in res.stdout:
                return "healthy", f"Traffic control htb queueing discipline running on '{lan}'."
            return "warning", f"No traffic shaping (htb) active on '{lan}'."
        except Exception as e:
            return "warning", f"Failed to check tc state on '{lan}': {e}"

    def check_serial(self) -> tuple[str, str]:
        import config as app_config
        port = app_config.SERIAL_PORT
        if port == "MOCK":
            return "healthy", "Mock serial driver is active."
        if port == "AUTO":
            return "healthy", "Serial port auto-detection configured."
        if not os.path.exists(port):
            return "warning", f"Configured serial device port '{port}' not found on host."
        return "healthy", f"Serial comport '{port}' is accessible."

    def check_templates(self) -> tuple[str, str]:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        generated = [
            os.path.join(base_dir, "config", "systemd", "pisowifi-backend.service"),
            os.path.join(base_dir, "config", "nginx", "pisowifi.conf"),
            os.path.join(base_dir, "config", "dnsmasq", "dnsmasq.conf"),
        ]
        missing = [f for f in generated if not os.path.exists(f)]
        if missing:
            return "critical", f"Generated config files are missing: {', '.join([os.path.basename(m) for m in missing])}."
        return "healthy", "All dynamic template configurations generated successfully."

    def check_permissions(self) -> tuple[str, str]:
        import config as app_config
        run_dir = app_config.RUN_DIR
        if not os.path.exists(run_dir):
            return "critical", f"Runtime folder '{run_dir}' does not exist."
        if not os.access(run_dir, os.W_OK):
            return "critical", f"Runtime folder '{run_dir}' is not writable by current process."
        return "healthy", f"Runtime directories are readable and writable."

    def check_internet(self) -> tuple[str, str]:
        try:
            socket.setdefaulttimeout(3)
            socket.gethostbyname("dns.google")
            res = httpx.get("https://www.google.com", timeout=3.0)
            if res.status_code == 200:
                return "healthy", "Public internet connectivity verified."
            return "warning", "Public ping succeeded but HTTP GET failed."
        except Exception as e:
            return "warning", f"Internet connectivity check failed: {e}."
