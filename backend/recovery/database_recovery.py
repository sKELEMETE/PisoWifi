import logging
import time

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from database import engine

logger = logging.getLogger(__name__)


class DatabaseRecovery:
    """
    Keeps retrying until MariaDB is available again.
    Raises RuntimeError after MAX_RETRIES attempts.
    """

    RETRY_SECONDS = 5
    MAX_RETRIES = 60

    def wait_until_available(self):
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

                logger.info("Database connected after %d attempt(s).", attempt)
                return

            except OperationalError:
                logger.warning(
                    "Database unavailable (attempt %d/%d). Retrying in %ds...",
                    attempt, self.MAX_RETRIES, self.RETRY_SECONDS,
                )
                if attempt == self.MAX_RETRIES:
                    raise RuntimeError(
                        f"Database did not become available after "
                        f"{self.MAX_RETRIES} retries ({self.MAX_RETRIES * self.RETRY_SECONDS}s)."
                    )
                time.sleep(self.RETRY_SECONDS)
