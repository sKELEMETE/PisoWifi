import os
import shutil
import subprocess
import logging
from datetime import datetime, timedelta
import config
from utils.time_utils import get_utc_now

logger = logging.getLogger(__name__)


class BackupService:
    def __init__(self, backup_dir: str | None = None, retention_days: int = 30):
        self.backup_dir = backup_dir or config.BACKUP_DIRECTORY
        self.retention_days = retention_days

    def _ensure_backup_dir(self):
        os.makedirs(self.backup_dir, exist_ok=True)

    def _cleanup_old_backups(self):
        """Remove backup files older than retention_days or keep latest 30 backups."""
        try:
            now = get_utc_now()
            cutoff = now - timedelta(days=self.retention_days)
            files = []
            for fname in os.listdir(self.backup_dir):
                fpath = os.path.join(self.backup_dir, fname)
                if os.path.isfile(fpath) and (fname.startswith("pisowifi_backup_") or fname.endswith(".sql") or fname.endswith(".db")):
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    files.append((fpath, mtime))

            # Sort files by modification time descending
            files.sort(key=lambda x: x[1], reverse=True)

            # Keep at most 30 most recent backups; remove older files beyond retention cutoff
            for idx, (fpath, mtime) in enumerate(files):
                if idx >= 30 or mtime < cutoff:
                    try:
                        os.remove(fpath)
                        logger.info("Backup retention: removed old backup file %s", os.path.basename(fpath))
                    except Exception as exc:
                        logger.warning("Failed to remove old backup file %s: %s", fpath, exc)
        except Exception as exc:
            logger.warning("Error during backup retention cleanup: %s", exc)

    def run_backup(self) -> str:
        """
        Executes a database backup operation.
        Supports MariaDB/MySQL via mysqldump with SQLite fallback.
        Returns the absolute path of the created backup file.
        """
        self._ensure_backup_dir()
        timestamp = get_utc_now().strftime("%Y%m%d_%H%M%S")
        db_type = config.DATABASE_TYPE.lower()

        backup_file = None
        if db_type in ("mysql", "mariadb"):
            mysqldump_bin = shutil.which("mysqldump") or "/usr/bin/mysqldump"
            if os.path.exists(mysqldump_bin):
                backup_file = os.path.join(self.backup_dir, f"pisowifi_backup_{timestamp}.sql")
                defaults_file = os.path.join(self.backup_dir, f".my_{timestamp}.cnf")
                try:
                    with open(defaults_file, "w") as f_cnf:
                        f_cnf.write(
                            "[client]\n"
                            f"host={config.DATABASE_HOST}\n"
                            f"port={config.DATABASE_PORT}\n"
                            f"user={config.DATABASE_USER}\n"
                            f"password={config.DATABASE_PASSWORD}\n"
                        )
                    os.chmod(defaults_file, 0o600)

                    cmd = [
                        mysqldump_bin,
                        f"--defaults-extra-file={defaults_file}",
                        "--single-transaction",
                        "--quick",
                        config.DATABASE_NAME,
                    ]
                    logger.info("Running mysqldump backup to %s...", backup_file)
                    with open(backup_file, "w") as f_out:
                        res = subprocess.run(
                            cmd,
                            stdout=f_out,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=120,
                        )
                    if res.returncode != 0:
                        err_msg = res.stderr.strip() if res.stderr else f"Exit code {res.returncode}"
                        logger.error("mysqldump failed with error: %s", err_msg)
                        if os.path.exists(backup_file):
                            os.remove(backup_file)
                        backup_file = None
                    elif not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
                        logger.error("mysqldump generated an empty backup file.")
                        if os.path.exists(backup_file):
                            os.remove(backup_file)
                        backup_file = None
                    else:
                        logger.info("mysqldump completed successfully. File size: %d bytes", os.path.getsize(backup_file))
                except Exception as exc:
                    logger.error("mysqldump subprocess execution failed: %s", exc)
                    if backup_file and os.path.exists(backup_file):
                        try:
                            os.remove(backup_file)
                        except Exception:
                            pass
                    backup_file = None
                finally:
                    if os.path.exists(defaults_file):
                        try:
                            os.remove(defaults_file)
                        except Exception:
                            pass

        # Fallback to SQLite backup if database is SQLite or mysqldump failed/unavailable
        if backup_file is None:
            sqlite_db_path = os.path.join(config.BASE_DIR, "pisowifi.db")
            if os.path.exists(sqlite_db_path):
                backup_file = os.path.join(self.backup_dir, f"pisowifi_backup_{timestamp}.db")
                logger.info("Creating SQLite database file copy backup to %s...", backup_file)
                try:
                    shutil.copy2(sqlite_db_path, backup_file)
                    if os.path.exists(backup_file) and os.path.getsize(backup_file) > 0:
                        logger.info("SQLite backup completed successfully. File size: %d bytes", os.path.getsize(backup_file))
                    else:
                        raise RuntimeError("SQLite backup file copy is zero bytes.")
                except Exception as exc:
                    logger.error("SQLite database file copy failed: %s", exc)
                    if os.path.exists(backup_file):
                        try:
                            os.remove(backup_file)
                        except Exception:
                            pass
                    raise RuntimeError(f"Database backup failed: {exc}")
            else:
                raise RuntimeError("Database backup failed: mysqldump unavailable and SQLite database file not found.")

        # Backup configuration files alongside the database
        self._backup_config_files(timestamp)

        # Cleanup old backups according to retention policy
        self._cleanup_old_backups()
        return backup_file

    def _backup_config_files(self, timestamp: str):
        """Copy important configuration files into the backup directory."""
        config_files = {
            "env": os.path.join(config.BASE_DIR, ".env"),
            "dnsmasq": "/etc/dnsmasq.conf",
            "nginx": "/etc/nginx/nginx.conf",
            "nftables": "/etc/nftables.conf",
        }
        for label, src in config_files.items():
            if os.path.exists(src):
                dst = os.path.join(self.backup_dir, f"config_{label}_{timestamp}.bak")
                try:
                    shutil.copy2(src, dst)
                    logger.info("Config backup: %s -> %s", src, dst)
                except Exception as exc:
                    logger.warning("Failed to backup config %s (%s): %s", label, src, exc)
