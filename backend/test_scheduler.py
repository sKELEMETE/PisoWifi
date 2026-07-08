import time

from scheduler.scheduler_service import SchedulerService

scheduler = SchedulerService()
scheduler.start()

print("Scheduler started.")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    scheduler.stop()
    print("Scheduler stopped.")
