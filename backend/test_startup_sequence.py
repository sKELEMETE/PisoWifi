from database import SessionLocal

from recovery.database_recovery import DatabaseRecovery
from recovery.firewall_recovery import FirewallRecovery
from recovery.power_recovery import PowerRecovery
from recovery.session_recovery import SessionRecovery
from recovery.startup_sequence import StartupSequence

from repositories.session_repository import SessionRepository
from services.firewall_service import FirewallService

db = SessionLocal()

repo = SessionRepository(db)

startup = StartupSequence(
    database_recovery=DatabaseRecovery(),
    power_recovery=PowerRecovery(repo, db),
    session_recovery=SessionRecovery(repo),
    firewall_recovery=FirewallRecovery(
        repo,
        FirewallService(),
    ),
)

startup.run()

db.close()
