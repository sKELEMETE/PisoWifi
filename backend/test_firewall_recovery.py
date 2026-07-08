from database import SessionLocal

from recovery.firewall_recovery import FirewallRecovery
from repositories.session_repository import SessionRepository
from services.firewall_service import FirewallService

db = SessionLocal()

repo = SessionRepository(db)
firewall = FirewallService()

recovery = FirewallRecovery(
    repo,
    firewall,
)

count = recovery.rebuild()

print(f"Recovered {count} authenticated clients.")

db.close()
