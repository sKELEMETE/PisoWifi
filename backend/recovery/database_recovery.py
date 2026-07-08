import time

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from database import engine


class DatabaseRecovery:
    """
    Keeps retrying until MariaDB is available again.
    """

    RETRY_SECONDS = 5

    def wait_until_available(self):
        while True:
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

                print("[Recovery] Database connected.")
                return

            except OperationalError:
                print(
                    f"[Recovery] Database unavailable. "
                    f"Retrying in {self.RETRY_SECONDS}s..."
                )
                time.sleep(self.RETRY_SECONDS)
