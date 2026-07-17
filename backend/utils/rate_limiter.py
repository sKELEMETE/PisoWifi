import time

class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, lock_duration: int = 900):
        self.max_attempts = max_attempts
        self.lock_duration = lock_duration
        # In-memory dictionary: IP -> { "attempts": int, "lockout_until": float }
        self.records = {}

    def is_locked(self, ip: str) -> tuple[bool, int]:
        """
        Returns (locked, remaining_seconds)
        """
        now = time.time()
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
        record = self.records.setdefault(ip, {"attempts": 0, "lockout_until": 0})
        
        # If currently locked out, do nothing
        if record["lockout_until"] > now:
            return
            
        record["attempts"] += 1
        if record["attempts"] >= self.max_attempts:
            record["lockout_until"] = now + self.lock_duration

    def reset(self, ip: str):
        if ip in self.records:
            self.records[ip] = {"attempts": 0, "lockout_until": 0}

# Global singleton instance
login_limiter = LoginRateLimiter()
