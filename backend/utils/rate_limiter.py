import os
import time
import logging
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

_process_warning_issued = False


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, lock_duration: int = 900, max_records: int = 5000):
        self.max_attempts = max_attempts
        self.lock_duration = lock_duration
        self.max_records = max_records
        # In-memory dictionary: IP -> { "attempts": int, "lockout_until": float }
        self.records = {}
        self._lock = Lock()
        self._last_cleanup = time.time()

    def _cleanup_unlocked(self, now: float):
        if len(self.records) > self.max_records or (now - self._last_cleanup) > 300:
            stale_keys = [
                ip for ip, rec in self.records.items()
                if rec.get("lockout_until", 0) <= now and rec.get("attempts", 0) == 0
            ]
            for ip in stale_keys:
                del self.records[ip]
            self._last_cleanup = now

    def is_locked(self, ip: str) -> tuple[bool, int]:
        """
        Returns (locked, remaining_seconds)
        """
        now = time.time()
        with self._lock:
            self._cleanup_unlocked(now)
            record = self.records.get(ip)
            if not record:
                return False, 0
            
            lockout_until = record.get("lockout_until", 0)
            if now < lockout_until:
                remaining = int(lockout_until - now)
                return True, remaining
            
            # Lockout expired, clean up attempts
            if lockout_until > 0 and now >= lockout_until:
                record["attempts"] = 0
                record["lockout_until"] = 0
                
            return False, 0

    def record_failure(self, ip: str):
        now = time.time()
        with self._lock:
            self._cleanup_unlocked(now)
            record = self.records.setdefault(ip, {"attempts": 0, "lockout_until": 0})
            
            # If currently locked out, do nothing
            if record["lockout_until"] > now:
                return
                
            record["attempts"] += 1
            if record["attempts"] >= self.max_attempts:
                record["lockout_until"] = now + self.lock_duration

    def reset(self, ip: str):
        with self._lock:
            if ip in self.records:
                self.records[ip] = {"attempts": 0, "lockout_until": 0}


class VoucherRateLimiter:
    """
    Rate limiter for voucher redemption attempts.
    Bounded memory with automatic TTL cleanup and multi-key evaluation support.
    """
    def __init__(self, max_attempts: int = 10, window_seconds: int = 60, lock_duration: int = 300, max_records: int = 5000):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lock_duration = lock_duration
        self.max_records = max_records
        # key -> { "attempts": [timestamps], "lockout_until": float }
        self.records = defaultdict(lambda: {"attempts": [], "lockout_until": 0})
        self._lock = Lock()
        self._last_cleanup = time.time()

    def _cleanup_stale(self, now: float):
        if len(self.records) > self.max_records or (now - self._last_cleanup) > 300:
            cutoff = now - self.window_seconds
            stale_keys = []
            for key, record in list(self.records.items()):
                record["attempts"] = [t for t in record["attempts"] if t > cutoff]
                if record["lockout_until"] <= now and len(record["attempts"]) == 0:
                    stale_keys.append(key)
            for k in stale_keys:
                self.records.pop(k, None)
            self._last_cleanup = now

    def is_locked(self, key: str) -> tuple[bool, int]:
        """
        Returns (locked, remaining_seconds)
        """
        now = time.time()
        with self._lock:
            self._cleanup_stale(now)
            record = self.records.get(key)
            if not record:
                return False, 0
            
            lockout_until = record.get("lockout_until", 0)
            if now < lockout_until:
                remaining = int(lockout_until - now)
                return True, remaining
            
            # Lockout expired, clean up
            if lockout_until > 0 and now >= lockout_until:
                record["attempts"] = []
                record["lockout_until"] = 0
                
            return False, 0

    def record_attempt(self, key: str, success: bool = False):
        now = time.time()
        with self._lock:
            self._cleanup_stale(now)
            record = self.records[key]
            
            # If currently locked out, do nothing
            if record["lockout_until"] > now:
                return
            
            if success:
                # Reset on successful redemption
                record["attempts"] = []
                record["lockout_until"] = 0
                return
            
            # Record failed attempt
            record["attempts"].append(now)
            
            # Clean old attempts outside the window
            cutoff = now - self.window_seconds
            record["attempts"] = [t for t in record["attempts"] if t > cutoff]
            
            # Check if limit exceeded
            if len(record["attempts"]) >= self.max_attempts:
                record["lockout_until"] = now + self.lock_duration

    def reset(self, key: str):
        with self._lock:
            if key in self.records:
                self.records[key] = {"attempts": [], "lockout_until": 0}


# Global singleton instances
login_limiter = LoginRateLimiter()
voucher_limiter = VoucherRateLimiter()

# Detect multi-worker deployments and warn about in-memory limitation.
# Each worker process has its own independent rate limiter state,
# meaning rate limits are per-process, not global.
if not _process_warning_issued:
    _process_warning_issued = True
    workers = os.environ.get("UVICORN_WORKERS") or os.environ.get("GUNICORN_WORKERS") or ""
    if workers and int(workers) > 1:
        logger.warning(
            "In-memory rate limiter active with %s workers. "
            "Rate limits are per-process, not global. "
            "Consider a shared backend (Redis) for multi-worker deployments.",
            workers,
        )
