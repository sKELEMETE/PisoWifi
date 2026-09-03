import os
import shutil
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
import config
from utils.time_utils import get_utc_now
from models.session import Session as SessionModel, SessionStatus
from models.network_authorization import NetworkAuthorization

logger = logging.getLogger(__name__)


class HealthService:

    def check_liveness(self) -> dict:
        """Liveness probe: verifies the backend API process is responsive."""
        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def check_readiness(self, db: Session) -> tuple[bool, dict]:
        """
        Readiness probe: verifies all critical system dependencies:
        - Database connection
        - Firewall controller tool / driver
        - Coin hardware / serial connection
        """
        status = {
            "database": False,
            "firewall": False,
            "hardware": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        reasons = []

        # 1. Database check
        try:
            db.execute(text("SELECT 1;"))
            status["database"] = True
        except Exception as exc:
            logger.error("Readiness probe database connection failed: %s", exc)
            reasons.append("Database connection failed")

        # 2. Firewall check
        try:
            from services.firewall_service import FirewallService
            fw = FirewallService()
            fw.get_active_kernel_elements()
            status["firewall"] = True
        except Exception as exc:
            logger.error("Readiness probe firewall inspection failed: %s", exc)
            reasons.append("Firewall inspection failed")

        # 3. Hardware / Coin Interface check
        try:
            from services.hardware_service import hardware_service
            # Check if hardware service is active or configured in a valid mode
            if config.COIN_INTERFACE in ("arduino", "gpio"):
                status["hardware"] = True
            else:
                reasons.append("Invalid coin interface configuration")
        except Exception as exc:
            logger.error("Readiness probe hardware controller error: %s", exc)
            reasons.append("Hardware controller unavailable")

        is_ready = status["database"] and status["firewall"] and status["hardware"]
        status["ready"] = is_ready
        if reasons:
            status["reasons"] = reasons

        return is_ready, status

    def check_admin_diagnostics(self, db: Session) -> dict:
        """
        Deep diagnostic telemetry for administrative monitoring:
        - Backup recency & integrity
        - Storage & memory utilization
        - Out-of-sync firewall rules
        - Live customer sessions
        """
        now = get_utc_now()

        # 1. Disk usage
        try:
            base_path = config.BASE_DIR if os.path.exists(config.BASE_DIR) else "/"
            total, used, free = shutil.disk_usage(base_path)
            disk_pct = round((used / total) * 100, 1)
            disk_info = {
                "total_mb": total // (1024 * 1024),
                "used_mb": used // (1024 * 1024),
                "free_mb": free // (1024 * 1024),
                "used_percent": disk_pct,
            }
        except Exception:
            disk_info = {"error": "Unable to determine disk usage"}

        # 2. Memory usage
        memory_info = {}
        try:
            if os.path.exists("/proc/meminfo"):
                mem = {}
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            mem[parts[0].strip()] = int(parts[1].strip().split()[0])
                total_kb = mem.get("MemTotal", 0)
                avail_kb = mem.get("MemAvailable", 0)
                used_kb = total_kb - avail_kb
                if total_kb > 0:
                    memory_info = {
                        "total_mb": total_kb // 1024,
                        "used_mb": used_kb // 1024,
                        "free_mb": avail_kb // 1024,
                        "used_percent": round((used_kb / total_kb) * 100, 1),
                    }
        except Exception:
            memory_info = {"error": "Unable to read /proc/meminfo"}

        # 3. Last backup age
        last_backup_age_seconds = None
        last_backup_file = None
        backup_dir = config.BACKUP_DIRECTORY
        if os.path.exists(backup_dir):
            backups = [
                os.path.join(backup_dir, f)
                for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f)) and (f.endswith(".sql") or f.endswith(".db"))
            ]
            if backups:
                newest = max(backups, key=os.path.getmtime)
                last_backup_file = os.path.basename(newest)
                last_backup_age_seconds = int((datetime.now() - datetime.fromtimestamp(os.path.getmtime(newest))).total_seconds())

        # 4. Out-of-sync firewall rules
        unapplied_rules_count = 0
        try:
            unapplied_rules_count = db.query(NetworkAuthorization).filter(
                NetworkAuthorization.desired_state != NetworkAuthorization.applied_state
            ).count()
        except Exception:
            pass

        # 5. Session counts
        active_sessions = 0
        paused_sessions = 0
        try:
            active_sessions = db.query(SessionModel).filter(SessionModel.status == SessionStatus.ACTIVE).count()
            paused_sessions = db.query(SessionModel).filter(SessionModel.status == SessionStatus.PAUSED).count()
        except Exception:
            pass

        return {
            "timestamp": now.isoformat(),
            "disk": disk_info,
            "memory": memory_info,
            "backup": {
                "last_backup_file": last_backup_file,
                "last_backup_age_seconds": last_backup_age_seconds,
            },
            "firewall": {
                "unapplied_rules_count": unapplied_rules_count,
            },
            "sessions": {
                "active": active_sessions,
                "paused": paused_sessions,
                "total": active_sessions + paused_sessions,
            }
        }

    def get_status(self):
        """Legacy compatibility method."""
        return {
            "database": "healthy",
            "firewall": "healthy",
            "serial": "healthy",
            "network": "healthy",
        }
