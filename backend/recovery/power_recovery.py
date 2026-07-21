import logging
from datetime import datetime
from utils.time_utils import get_utc_now
from models.session import SessionStatus

logger = logging.getLogger(__name__)


class PowerRecovery:
    """
    Converts all ACTIVE sessions to PAUSED after an
    unexpected shutdown or power failure.
    """

    def __init__(
        self,
        session_repository,
        db,
    ):
        self.session_repository = session_repository
        self.db = db

    def recover(self):
        logger.info("Starting power recovery...")

        # Check system uptime to distinguish a system reboot (power failure) from a backend restart.
        is_system_reboot = False
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.read().split()[0])
                # If system booted less than 120 seconds ago, it is a hardware reboot/power cycle
                if uptime_seconds < 120:
                    is_system_reboot = True
        except (FileNotFoundError, PermissionError, ValueError, OSError) as exc:
            logger.warning("Could not read system uptime, defaulting to False: %s", exc)

        if not is_system_reboot:
            logger.info("System uptime is healthy. Treating as a clean backend restart. Skipping active session pausing.")
            return 0

        sessions = self.session_repository.get_active_sessions()

        recovered = 0
        now = get_utc_now()

        for session in sessions:
            session.status = SessionStatus.PAUSED
            session.paused_at = now
            rem_sec = max(0, int((session.end_time - now).total_seconds()))
            session.remaining_seconds = rem_sec
            session.remaining_minutes = rem_sec // 60
            recovered += 1


        self.db.commit()

        logger.info(
            "Power recovery complete. %s sessions paused.",
            recovered,
        )

        return recovered
