import logging

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    Coordinates clean backend shutdown.
    """

    def __init__(
        self,
        scheduler,
        db,
    ):
        self.scheduler = scheduler
        self.db = db

    def shutdown(self):
        logger.info("========== SHUTDOWN ==========")

        if self.scheduler.running:
            logger.info("Stopping scheduler...")
            self.scheduler.shutdown(wait=True)

        logger.info("Closing database...")
        self.db.close()

        logging.shutdown()

        print("System shutdown completed.")
