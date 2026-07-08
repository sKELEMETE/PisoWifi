from database import SessionLocal

from recovery.power_recovery import PowerRecovery
from repositories.session_repository import SessionRepository

db = SessionLocal()

repo = SessionRepository(db)

recovery = PowerRecovery(
    repo,
    db,
)

count = recovery.recover()

print(f"Paused {count} active sessions.")

db.close()
