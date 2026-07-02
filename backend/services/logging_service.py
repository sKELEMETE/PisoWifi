import logging


class LoggingService:

    def __init__(self):
        self.logger = logging.getLogger("pisowifi")

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)
