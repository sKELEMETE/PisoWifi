from database import SessionLocal

from recovery.session_recovery import SessionRecovery
from repositories.session_repository import SessionRepository

db = SessionLocal()

repo = SessionRepository(db)

recovery = SessionRecovery(repo)

result = recovery.recover()

print()

print("ACTIVE :", len(result["active"]))
print("PAUSED :", len(result["paused"]))

db.close()
