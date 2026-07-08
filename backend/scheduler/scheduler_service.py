from apscheduler.schedulers.background import BackgroundScheduler

import config

from scheduler.jobs import (
    backup,
    check_health,
    cleanup,
    expire_sessions,
    sync_firewall,
)


class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def start(self):
        interval = config.SCHEDULER_INTERVAL

        self.scheduler.add_job(
            expire_sessions,
            "interval",
            seconds=interval,
            id="expire_sessions",
        )

        self.scheduler.add_job(
            sync_firewall,
            "interval",
            seconds=interval,
            id="sync_firewall",
        )

        self.scheduler.add_job(
            check_health,
            "interval",
            seconds=interval,
            id="health",
        )

        self.scheduler.add_job(
            cleanup,
            "interval",
            minutes=30,
            id="cleanup",
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
