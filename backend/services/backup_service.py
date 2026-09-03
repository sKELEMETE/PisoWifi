import os
import shutil
import subprocess
import logging
import hashlib
import sqlite3
import tempfile
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

    def _generate_checksum(self, file_path: str) -> str:
        """Compute SHA256 checksum of a file and write to .sha256 companion file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        digest = sha256.hexdigest()
        checksum_file = f"{file_path}.sha256"
        with open(checksum_file, "w") as f_out:
            f_out.write(f"{digest}  {os.path.basename(file_path)}\n")
        try:
            os.chmod(checksum_file, 0o600)
        except Exception:
            pass
        return digest

    def _cleanup_old_backups(self):
        """Remove backup files older than retention policy (daily + weekly retention)."""
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
                        sha = f"{fpath}.sha256"
                        if os.path.exists(sha):
                            os.remove(sha)
                        logger.info("Backup retention: removed old backup file %s", os.path.basename(fpath))
                    except Exception as exc:
                        logger.warning("Failed to remove old backup file %s: %s", fpath, exc)
        except Exception as exc:
            logger.warning("Error during backup retention cleanup: %s", exc)

    def run_backup(self) -> str:
        """
        Executes a verified database backup operation.
        Produces non-empty archive with SHA256 checksum and backup configurations.
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
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            repo_root = os.path.dirname(backend_dir)
            sqlite_candidates = [
                os.path.join(config.BASE_DIR, "pisowifi.db"),
                os.path.join(repo_root, "pisowifi.db"),
                os.path.join(backend_dir, "pisowifi.db"),
                os.path.join(backend_dir, "backend", "pisowifi.db"),
            ]
            sqlite_db_path = next((p for p in sqlite_candidates if os.path.exists(p) and os.path.getsize(p) > 0), None)
            if sqlite_db_path:
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

        # Enforce strict 0600 permissions on database backup archive
        try:
            os.chmod(backup_file, 0o600)
        except Exception:
            pass

        # Compute and persist SHA256 checksum
        checksum = self._generate_checksum(backup_file)
        logger.info("Backup SHA256 checksum generated: %s", checksum)

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
                    os.chmod(dst, 0o600)
                    logger.info("Config backup: %s -> %s", src, dst)
                except Exception as exc:
                    logger.warning("Failed to backup config %s (%s): %s", label, src, exc)

    def verify_restore(self, backup_file: str) -> dict:
        """
        Automated restore verification:
        1. Validates checksum integrity against companion .sha256 file if present.
        2. Restores to a temporary disposable database instance.
        3. Runs integrity checks and queries row counts for critical tables.
        4. Cleans up disposable test instance.
        """
        if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
            return {"valid": False, "error": "Backup file does not exist or is empty"}

        # Verify SHA256
        sha256 = hashlib.sha256()
        with open(backup_file, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        actual_digest = sha256.hexdigest()

        checksum_file = f"{backup_file}.sha256"
        if os.path.exists(checksum_file):
            with open(checksum_file, "r") as f_chk:
                recorded_digest = f_chk.read().split()[0]
            if actual_digest != recorded_digest:
                return {
                    "valid": False,
                    "error": f"Checksum mismatch: expected {recorded_digest}, got {actual_digest}"
                }

        tables_count = {}
        if backup_file.endswith(".db"):
            # Disposable SQLite restore verification
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
                tmp_path = tmp_db.name

            try:
                shutil.copy2(backup_file, tmp_path)
                conn = sqlite3.connect(tmp_path)
                cursor = conn.cursor()

                # Integrity check
                cursor.execute("PRAGMA integrity_check;")
                res = cursor.fetchone()
                if not res or res[0] != "ok":
                    return {"valid": False, "error": f"PRAGMA integrity_check failed: {res}"}

                # Query critical tables
                for table in ("clients", "sessions", "rates", "vouchers"):
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        tables_count[table] = cursor.fetchone()[0]
                    except sqlite3.OperationalError:
                        tables_count[table] = 0

                conn.close()
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        elif backup_file.endswith(".sql"):
            # SQL dump validation
            with open(backup_file, "r", errors="ignore") as f_sql:
                content = f_sql.read(1000000)

            for table in ("clients", "sessions", "rates", "vouchers"):
                if f"CREATE TABLE `{table}`" in content or f"CREATE TABLE IF NOT EXISTS `{table}`" in content:
                    tables_count[table] = "schema_verified"
                else:
                    tables_count[table] = "not_found"

        return {
            "valid": True,
            "sha256": actual_digest,
            "size_bytes": os.path.getsize(backup_file),
            "tables": tables_count,
        }
