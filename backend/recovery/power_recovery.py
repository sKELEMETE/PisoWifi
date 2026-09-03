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

    def recover(self, force: bool = False):
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

        if not is_system_reboot and not force:
            logger.info("System uptime is healthy. Treating as a clean backend restart. Skipping active session pausing.")
            return 0

        sessions = self.session_repository.get_active_sessions()

        recovered = 0
        now = get_utc_now()

        from models.session import ClientLiveSession

        for session in sessions:
            # CRITICAL: Preserve the durable checkpointed remaining_seconds.
            # Do NOT subtract wall-clock downtime when the machine was powered off!
            if session.remaining_seconds is not None and session.remaining_seconds > 0:
                rem_sec = session.remaining_seconds
            elif session.remaining_minutes and session.remaining_minutes > 0:
                rem_sec = session.remaining_minutes * 60
            else:
                rem_sec = max(0, int((session.end_time - now).total_seconds())) if session.end_time else 0

            session.status = SessionStatus.PAUSED
            session.paused_at = now
            session.last_accounted_at = now
            session.remaining_seconds = rem_sec
            session.remaining_minutes = rem_sec // 60

            # Sync ClientLiveSession status
            live = self.db.query(ClientLiveSession).filter(ClientLiveSession.client_id == session.client_id).first()
            if live:
                live.status = SessionStatus.PAUSED.value
                live.updated_at = now

            recovered += 1

        self.db.commit()

        logger.info(
            "Power recovery complete. %s sessions safely paused with time preserved.",
            recovered,
        )

        return recovered
