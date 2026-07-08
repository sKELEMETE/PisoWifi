import logging

logger = logging.getLogger(__name__)


class SessionRecovery:
    """
    Restores application runtime state from
    persistent database sessions.
    """

    def __init__(
        self,
        session_repository,
    ):
        self.session_repository = session_repository

    def recover(self):
        logger.info("Starting session recovery...")

        active_sessions = self.session_repository.get_active_sessions()
        paused_sessions = self.session_repository.get_paused_sessions()

        logger.info(
            "Recovered %s active session(s).",
            len(active_sessions),
        )

        logger.info(
            "Recovered %s paused session(s).",
            len(paused_sessions),
        )

        return {
            "active": active_sessions,
            "paused": paused_sessions,
        }
