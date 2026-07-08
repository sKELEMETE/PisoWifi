import logging

logger = logging.getLogger(__name__)


class StartupSequence:
    """
    Coordinates backend startup recovery.
    """

    def __init__(
        self,
        database_recovery,
        power_recovery,
        session_recovery,
        firewall_recovery,
    ):
        self.database_recovery = database_recovery
        self.power_recovery = power_recovery
        self.session_recovery = session_recovery
        self.firewall_recovery = firewall_recovery

    def run(self):
        logger.info("========== STARTUP ==========")

        logger.info("1. Waiting for database...")
        self.database_recovery.wait_until_available()

        logger.info("2. Running power recovery...")
        paused = self.power_recovery.recover()

        logger.info("Paused %s active session(s).", paused)

        logger.info("3. Recovering sessions...")
        sessions = self.session_recovery.recover()

        logger.info(
            "Recovered %s active, %s paused session(s).",
            len(sessions["active"]),
            len(sessions["paused"]),
        )

        logger.info("4. Rebuilding firewall...")
        restored = self.firewall_recovery.rebuild()

        logger.info(
            "Restored %s firewall authorization(s).",
            restored,
        )

        logger.info("========== SYSTEM READY ==========")
