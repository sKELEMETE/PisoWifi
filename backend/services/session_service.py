from datetime import datetime, timedelta
from repositories.session_repository import SessionRepository
from repositories.client_repository import ClientRepository
from services.firewall_service import FirewallService

class SessionService:
    def __init__(self, session_repository: SessionRepository):
        self.session_repository = session_repository
        self.client_repository = ClientRepository(self.session_repository.db)
        self.firewall = FirewallService()

    def create_or_extend_session(self, client_id: int, rate_id: int, minutes: int, authorize: bool = True, pause_allowed: bool = True, commit: bool = True):
        session = self.session_repository.get_active_session_by_client_id(client_id)
        paused_session = self.session_repository.get_paused_session_by_client_id(client_id)
        client = self.client_repository.get_by_id(client_id)
        now = datetime.now()

        if session:
            # Shift end point boundary forward dynamically
            session.end_time = session.end_time + timedelta(minutes=minutes)
            session.purchased_minutes += minutes
            session.remaining_minutes = int((session.end_time - now).total_seconds() / 60)
            session.pause_allowed = session.pause_allowed and pause_allowed
            if commit:
                self.session_repository.db.commit()
                self.session_repository.db.refresh(session)
        elif paused_session:
            # Extend existing paused session and activate it
            old_remaining_seconds = paused_session.remaining_minutes or 0
            new_seconds = minutes * 60
            total_seconds = old_remaining_seconds + new_seconds

            paused_session.status = "ACTIVE"
            paused_session.start_time = now
            paused_session.end_time = now + timedelta(seconds=total_seconds)
            paused_session.purchased_minutes += minutes
            paused_session.remaining_minutes = int(total_seconds / 60)
            paused_session.paused_at = None
            paused_session.pause_allowed = paused_session.pause_allowed and pause_allowed

            if commit:
                self.session_repository.db.commit()
                self.session_repository.db.refresh(paused_session)
            session = paused_session
        else:
            session = self.session_repository.create_session(
                client_id=client_id,
                rate_id=rate_id,
                minutes=minutes,
                pause_allowed=pause_allowed,
                commit=commit,
            )

        if client:
            client.status = "ONLINE"
            if commit:
                self.session_repository.db.commit()
            if client.current_ip and authorize:
                self.firewall.authorize(client.current_ip)

        return session