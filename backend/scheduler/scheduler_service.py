from apscheduler.schedulers.background import BackgroundScheduler

import config

from scheduler.jobs import (
    backup,
    check_expired_reservations_job,
    expire_sessions,
    sync_firewall,
)


class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def start(self):
        interval = config.SESSION_CHECK_INTERVAL

        self.scheduler.add_job(
            expire_sessions,
            "interval",
            seconds=interval,
            id="expire_sessions",
        )

        self.scheduler.add_job(
            check_expired_reservations_job,
            "interval",
            seconds=config.COIN_LEASE_CHECK_INTERVAL,
            id="expire_coin_lease",
            max_instances=1,
        )

        self.scheduler.add_job(
            sync_firewall,
            "interval",
            seconds=30,
            id="sync_firewall",
        )

        hour, minute = map(int, config.BACKUP_TIME.split(":"))

        self.scheduler.add_job(
            backup,
            "cron",
            hour=hour,
            minute=minute,
            id="backup",
        )

        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=True)
