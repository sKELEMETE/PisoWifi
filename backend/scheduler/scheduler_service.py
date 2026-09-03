import os
import time
import fcntl
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
import config
from scheduler.jobs import (
    backup,
    check_expired_reservations_job,
    expire_sessions,
    sync_firewall,
)

logger = logging.getLogger(__name__)


class SchedulerLock:
    def __init__(self, lock_file: str):
        self.lock_file = lock_file
        self._fd = None

    def acquire(self) -> bool:
        os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
        try:
            self._fd = open(self.lock_file, "w")
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._fd.write(f"{os.getpid()}\n")
            self._fd.flush()
            return True
        except (IOError, BlockingIOError):
            if self._fd:
                try:
                    self._fd.close()
                except Exception:
                    pass
                self._fd = None
            return False

    def release(self):
        if self._fd:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                self._fd.close()
            except Exception:
                pass
            self._fd = None


class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        lock_path = os.path.join(config.RUN_DIR, "scheduler.lock")
        self.lock = SchedulerLock(lock_path)
        self.is_leader = False
        self.metrics = {
            "is_leader": False,
            "jobs": {},
            "started_at": None,
        }

    def _instrument_job(self, job_name: str, job_func):
        if job_name not in self.metrics["jobs"]:
            self.metrics["jobs"][job_name] = {
                "runs": 0,
                "failures": 0,
                "last_run": None,
                "last_duration_ms": 0,
                "last_status": "PENDING",
            }

        def wrapped():
            stats = self.metrics["jobs"][job_name]
            stats["runs"] += 1
            stats["last_run"] = datetime.now(timezone.utc).isoformat()
            t0 = time.perf_counter()
            try:
                job_func()
                stats["last_status"] = "SUCCESS"
            except Exception as exc:
                stats["failures"] += 1
                stats["last_status"] = "FAILED"
                logger.error("Scheduler job '%s' raised exception: %s", job_name, exc)
            finally:
                stats["last_duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        wrapped.__name__ = f"instrumented_{job_name}"
        return wrapped

    def start(self):
        # Enforce scheduler singleton across uvicorn workers
        if not self.lock.acquire():
            logger.info("Scheduler lock held by another process; skipping scheduler in this worker.")
            self.is_leader = False
            self.metrics["is_leader"] = False
            return

        self.is_leader = True
        self.metrics["is_leader"] = True
        self.metrics["started_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("Scheduler lock acquired. Starting background scheduler singleton.")

        interval = config.SESSION_CHECK_INTERVAL

        self.scheduler.add_job(
            self._instrument_job("expire_sessions", expire_sessions),
            "interval",
            seconds=interval,
            id="expire_sessions",
            max_instances=1,
            coalesce=True,
        )

        self.scheduler.add_job(
            self._instrument_job("expire_coin_lease", check_expired_reservations_job),
            "interval",
            seconds=config.COIN_LEASE_CHECK_INTERVAL,
            id="expire_coin_lease",
            max_instances=1,
            coalesce=True,
        )

        self.scheduler.add_job(
            self._instrument_job("sync_firewall", sync_firewall),
            "interval",
            seconds=30,
            id="sync_firewall",
            max_instances=1,
            coalesce=True,
        )

        hour, minute = map(int, config.BACKUP_TIME.split(":"))

        self.scheduler.add_job(
            self._instrument_job("backup", backup),
            "cron",
            hour=hour,
            minute=minute,
            id="backup",
            max_instances=1,
            coalesce=True,
        )

        self.scheduler.start()

    def get_metrics(self) -> dict:
        return self.metrics

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        if self.is_leader:
            self.lock.release()
            self.is_leader = False
            self.metrics["is_leader"] = False
