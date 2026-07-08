import logging

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

        sessions = self.session_repository.get_active_sessions()

        recovered = 0

        for session in sessions:
            session.status = "PAUSED"
            recovered += 1

        self.db.commit()

        logger.info(
            "Power recovery complete. %s sessions paused.",
            recovered,
        )

        return recovered
