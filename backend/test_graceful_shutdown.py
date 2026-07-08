import logging

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from recovery.graceful_shutdown import GracefulShutdown

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

scheduler = BackgroundScheduler()

scheduler.start()

db = SessionLocal()

shutdown = GracefulShutdown(
    scheduler=scheduler,
    db=db,
)

shutdown.shutdown()
