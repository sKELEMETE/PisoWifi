import os
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.getenv("LOG_DIRECTORY", "/opt/pisowifi/logs")


def get_logger(name: str, log_filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
        except OSError:
            # Read-only development hosts must still be able to run dry-runs
            # and unit tests without impersonating a production install.
            fallback = os.path.join("/tmp", "pisowifi-logs")
            os.makedirs(fallback, exist_ok=True)
            log_dir = fallback
        else:
            log_dir = LOG_DIR
        log_path = os.path.join(log_dir, log_filename)

        handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(console)

    return logger
