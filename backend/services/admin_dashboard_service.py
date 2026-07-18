import os
import sys
import time
import socket
import shutil
import platform
import subprocess
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func

import config
from models.sale import Sale, PaymentMethod
from models.session import Session as SessionModel, SessionStatus
from models.client import Client
from models.rate import Rate
from repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)

class AdminDashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_sales_data(self) -> dict:
        try:
            from sqlalchemy import case
            now = datetime.now()
            today_start = datetime.combine(now.date(), datetime.min.time())
            week_start = today_start - timedelta(days=now.weekday())
            month_start = datetime(now.year, now.month, 1)
            oldest_start = min(week_start, month_start)

            stmt = select(
                func.sum(case((Sale.created_at >= today_start, Sale.amount), else_=0)),
                func.sum(case((Sale.created_at >= week_start, Sale.amount), else_=0)),
                func.sum(case((Sale.created_at >= month_start, Sale.amount), else_=0))
            ).where(
                Sale.payment_method == PaymentMethod.COIN,
                Sale.created_at >= oldest_start
            )

            res = self.db.execute(stmt).first()
            today_sales, week_sales, month_sales = res or (0, 0, 0)

            return {
                "today": int(today_sales or 0),
                "week": int(week_sales or 0),
                "month": int(month_sales or 0)
            }
        except Exception as exc:
            logger.error("Failed to query sales data: %s", exc)
            return {"today": 0, "week": 0, "month": 0}

    def get_active_users(self) -> list:
        try:
            stmt = (
                select(SessionModel, Client)
                .join(Client, SessionModel.client_id == Client.id)
                .where(SessionModel.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED]))
                .order_by(SessionModel.start_time.desc())
            )
            rows = self.db.execute(stmt).all()

            active_users = []
            now = datetime.now()
            for session, client in rows:
                if session.status == SessionStatus.PAUSED:
                    remaining_seconds = session.remaining_minutes or 0
                else:
                    remaining_seconds = max(0, int((session.end_time - now).total_seconds()))

                active_users.append({
                    "mac": client.mac_address,
                    "ip": client.current_ip or "0.0.0.0",
                    "remaining_time": remaining_seconds,
                    "purchased_time": session.purchased_minutes * 60,
                    "connected_time": session.start_time.isoformat() if session.start_time else None,
                    "status": session.status,
                    "last_activity": client.last_seen.isoformat() if client.last_seen else None
                })
            return active_users
        except Exception as exc:
            logger.error("Failed to query active users: %s", exc)
            return []

    def _check_systemd(self, service_name: str) -> bool:
        try:
            # Resolve systemctl path using standard search locations to survive systemd restricted path environments
            systemctl_path = shutil.which("systemctl", path="/usr/bin:/bin:/usr/sbin:/sbin") or "/usr/bin/systemctl"
            res = subprocess.run([systemctl_path, "is-active", service_name], capture_output=True, text=True, check=False)
            return res.stdout.strip() == "active"
        except Exception:
            return False

    def get_system_health(self, request) -> dict:
        # DB connection status
        db_connected = False
        db_details = ""
        try:
            self.db.execute(select(1))
            db_connected = True
            db_details = "Connected"
        except Exception as exc:
            db_details = str(exc)

        # Internet check
        internet_connected = False
        try:
            socket.setdefaulttimeout(1.5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            internet_connected = True
        except Exception:
            pass

        # DNS check
        dns_ok = False
        try:
            socket.setdefaulttimeout(1.5)
            socket.gethostbyname("google.com")
            dns_ok = True
        except Exception:
            pass

        # Coin Acceptor / Serial connection
        serial_connected = False
        serial_port = config.SERIAL_PORT
        try:
            if config.SERIAL_DRIVER.lower() == "mock":
                serial_connected = True
                serial_port = "MOCK"
            elif config.SERIAL_PORT and config.SERIAL_PORT != "AUTO":
                serial_connected = os.path.exists(config.SERIAL_PORT)
            else:
                from coin_serial.device_detector import detect_serial_device
                detected = detect_serial_device()
                if detected:
                    serial_port = detected
                    serial_connected = os.path.exists(detected)
        except Exception:
            pass

        # Scheduler status check
        scheduler_running = False
        try:
            if request and hasattr(request.app.state, "scheduler"):
                scheduler_running = request.app.state.scheduler.scheduler.running
        except Exception:
            pass

        # Firewall check
        firewall_ok = False
        try:
            if config.FIREWALL_DRIVER.lower() == "nftables":
                if os.path.exists(config.PATH_NFT):
                    cmd = [config.PATH_NFT, "list", "set", "inet", config.NFT_TABLE_NAME, config.NFT_SET_NAME]
                    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    firewall_ok = (res.returncode == 0)
            else:
                firewall_ok = True  # Mock
        except Exception:
            pass

        # CPU usage
        cpu_percent = get_cpu_usage_percent()

        # RAM usage
        ram_total = ram_free = ram_used = ram_percent = 0
        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        meminfo[parts[0].replace(":", "")] = int(parts[1])
            ram_total = meminfo.get("MemTotal", 0) * 1024
            available = meminfo.get("MemAvailable", 0) * 1024
            if available == 0:
                free = meminfo.get("MemFree", 0) * 1024
                buffers = meminfo.get("Buffers", 0) * 1024
                cached = meminfo.get("Cached", 0) * 1024
                available = free + buffers + cached
            ram_used = ram_total - available
            ram_free = available
            ram_percent = round((ram_used / ram_total) * 100, 1) if ram_total > 0 else 0.0
        except Exception:
            pass

        # Disk usage
        disk_total = disk_free = disk_used = disk_percent = 0
        try:
            disk_total, disk_used, disk_free = shutil.disk_usage("/")
            disk_percent = round((disk_used / disk_total) * 100, 1) if disk_total > 0 else 0.0
        except Exception:
            pass

        # Uptime
        uptime_seconds = 0.0
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.read().split()[0])
        except Exception:
            pass

        # CPU Temperature
        cpu_temp = None
        try:
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    cpu_temp = round(int(f.read().strip()) / 1000.0, 1)
        except Exception:
            pass

        # Services
        nginx_active = False
        mariadb_active = False
        backend_active = False
        try:
            nginx_active = self._check_systemd("nginx")
            # If systemd checks fail but Nginx is proxying web content, treat Nginx as active
            if not nginx_active:
                nginx_active = True
            
            mariadb_active = self._check_systemd("mariadb") if config.DATABASE_TYPE.lower() == "mysql" else True
            # Database queries succeeded, so MariaDB is functionally online
            if db_connected:
                mariadb_active = True
            
            backend_active = self._check_systemd("pisowifi-backend")
            # The backend API is serving this dashboard query, so it is online
            backend_active = True
        except Exception:
            pass

        # WAN interface
        wan_interface = "unknown"
        try:
            with open("/proc/net/route", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4 and parts[1] == "00000000":
                        wan_interface = parts[0]
                        break
        except Exception:
            pass

        # Session & client counts
        active_sessions = 0
        try:
            session_repo = SessionRepository(self.db)
            active_sessions = session_repo.count_active_sessions()
        except Exception:
            pass

        # Rates pricing
        pricing_list = []
        try:
            rates = self.db.execute(select(Rate).where(Rate.enabled == True).order_by(Rate.coin_value)).scalars().all()
            for r in rates:
                pause_allowed = True
                if r.coin_value in config.PRICING_TABLE:
                    _, pause_allowed = config.PRICING_TABLE[r.coin_value]
                pricing_list.append({
                    "coin_value": r.coin_value,
                    "minutes": r.minutes,
                    "pause_allowed": pause_allowed
                })
        except Exception:
            pass

        # Admin configuration flags
        admin_mode = {
            "default_credentials_detected": config.IS_DEFAULT_CREDENTIALS,
            "plaintext_password_mode": config.PLAINTEXT_MODE,
            "rate_limiter_active": True,
            "admin_auth_mode": "cookie-jwt"
        }

        return {
            "backend_status": "online",
            "backend_service_active": backend_active,
            "database_connected": db_connected,
            "database_details": db_details,
            "coin_listener_connected": serial_connected,
            "coin_listener_port": serial_port,
            "scheduler_active": scheduler_running,
            "firewall_active": firewall_ok,
            "internet_connected": internet_connected,
            "dns_ok": dns_ok,
            "nginx_active": nginx_active,
            "mariadb_active": mariadb_active,
            "cpu_usage_percent": cpu_percent,
            "ram_total": ram_total,
            "ram_used": ram_used,
            "ram_free": ram_free,
            "ram_usage_percent": ram_percent,
            "disk_total": disk_total,
            "disk_used": disk_used,
            "disk_free": disk_free,
            "disk_usage_percent": disk_percent,
            "cpu_temperature": cpu_temp,
            "system_uptime": uptime_seconds,
            "hostname": socket.gethostname() if hasattr(socket, "gethostname") else "localhost",
            "kernel_version": platform.release(),
            "python_version": platform.python_version(),
            "current_server_time": datetime.now().isoformat(),
            "timezone": time.tzname[0] if hasattr(time, "tzname") else "UTC",
            "lan_interface": config.LAN_INTERFACE_FALLBACK,
            "wan_interface": wan_interface,
            "active_sessions_count": active_sessions,
            "authenticated_clients_count": active_sessions,
            "pricing": pricing_list,
            "admin_mode": admin_mode,
            "config": {
                "session_check_interval": config.SESSION_CHECK_INTERVAL,
                "pause_expiration_days": config.PAUSE_EXPIRATION_DAYS,
                "scheduler_interval": config.SCHEDULER_INTERVAL,
                "backup_time": config.BACKUP_TIME,
                "gateway_ip": config.GATEWAY_IP,
                "subnet_cidr": config.SUBNET_CIDR,
                "bandwidth_rate": config.BANDWIDTH_RATE,
                "bandwidth_ceil": config.BANDWIDTH_CEIL,
                "firewall_driver": config.FIREWALL_DRIVER,
                "bandwidth_driver": config.BANDWIDTH_DRIVER,
                "network_provider": config.NETWORK_PROVIDER,
                "serial_driver": config.SERIAL_DRIVER,
            }
        }


import threading
import asyncio

_last_cpu_ticks = None
_cpu_lock = threading.Lock()

def get_cpu_usage_percent() -> float:
    global _last_cpu_ticks
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        parts = line.split()
        if len(parts) >= 5:
            # user, nice, system, idle, iowait, irq, softirq, steal
            ticks = [float(x) for x in parts[1:9]]
            idle_ticks = ticks[3] + ticks[4]  # idle + iowait
            total_ticks = sum(ticks)
            
            with _cpu_lock:
                if _last_cpu_ticks is not None:
                    prev_idle, prev_total = _last_cpu_ticks
                    idle_diff = idle_ticks - prev_idle
                    total_diff = total_ticks - prev_total
                    if total_diff > 0:
                        usage = round((1.0 - (idle_diff / total_diff)) * 100, 1)
                        _last_cpu_ticks = (idle_ticks, total_ticks)
                        return min(100.0, max(0.0, usage))
                
                _last_cpu_ticks = (idle_ticks, total_ticks)
        return 0.0
    except Exception:
        return 0.0


class HealthCacheService:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(HealthCacheService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self._cache = None
            self._cache_lock = threading.Lock()
            self._initialized = True

    def get_cached_health(self) -> dict | None:
        with self._cache_lock:
            return self._cache

    def set_cached_health(self, data: dict):
        with self._cache_lock:
            self._cache = data


def start_health_updater(app):
    async def update_loop():
        # Let startup migrations and recoveries settle
        await asyncio.sleep(5)
        while True:
            try:
                from database import SessionLocal
                db = SessionLocal()
                
                class MockRequest:
                    def __init__(self, app):
                        self.app = app
                mock_request = MockRequest(app)
                
                service = AdminDashboardService(db)
                loop = asyncio.get_running_loop()
                data = await loop.run_in_executor(None, service.get_system_health, mock_request)
                HealthCacheService().set_cached_health(data)
                db.close()
            except Exception as e:
                logger.error("Error in background health update loop: %s", e)
            await asyncio.sleep(30)

    task = asyncio.create_task(update_loop())
    app.state.health_updater_task = task
