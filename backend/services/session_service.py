from datetime import datetime, timedelta
from utils.time_utils import get_utc_now
from repositories.session_repository import SessionRepository
from repositories.client_repository import ClientRepository
from services.firewall_service import FirewallService
from models.session import Session, SessionStatus, ClientLiveSession
from models.client import Client


class SessionService:
    def __init__(self, session_repository: SessionRepository, firewall_service: FirewallService | None = None):
        self.session_repository = session_repository
        self.db = self.session_repository.db
        self.client_repository = ClientRepository(self.db)
        self.firewall = firewall_service or FirewallService()

    def _sync_network_auth(self, client: Client, session_id: int | None, desired_state: str, now: datetime):
        from models.network_authorization import NetworkAuthorization
        auth = self.db.query(NetworkAuthorization).filter(NetworkAuthorization.client_id == client.id).with_for_update().first()
        if auth:
            auth.mac_address = client.mac_address
            auth.ip_address = client.current_ip
            auth.session_id = session_id
            auth.desired_state = desired_state
            auth.reconciliation_version += 1
            auth.updated_at = now
        else:
            auth = NetworkAuthorization(
                client_id=client.id,
                mac_address=client.mac_address,
                ip_address=client.current_ip,
                session_id=session_id,
                desired_state=desired_state,
                applied_state="BLOCKED",
                reconciliation_version=1,
                created_at=now,
                updated_at=now,
            )
            self.db.add(auth)
        return auth

    def _sync_live_session(self, client_id: int, session_id: int, status: str, now: datetime):
        live = self.db.query(ClientLiveSession).filter(ClientLiveSession.client_id == client_id).with_for_update().first()
        if live:
            live.session_id = session_id
            live.status = status
            live.updated_at = now
        else:
            live = ClientLiveSession(
                client_id=client_id,
                session_id=session_id,
                status=status,
                updated_at=now,
            )
            self.db.add(live)

    def create_or_extend_session(
        self,
        client_id: int,
        rate_id: int,
        minutes: int,
        authorize: bool = True,
        pause_allowed: bool = True,
        commit: bool = True
    ) -> Session:
        # Lock client row to prevent concurrent race conditions
        client = self.db.query(Client).filter(Client.id == client_id).with_for_update().first()
        now = get_utc_now()
        new_seconds = max(0, minutes * 60)

        # Check existing live session via ClientLiveSession
        live = self.db.query(ClientLiveSession).filter(ClientLiveSession.client_id == client_id).with_for_update().first()
        session = None
        if live:
            session = self.db.query(Session).filter(Session.id == live.session_id).with_for_update().first()

        if session and session.status == SessionStatus.ACTIVE:
            # Shift end time forward and update remaining_seconds
            current_rem = max(0, int((session.end_time - now).total_seconds()))
            total_seconds = current_rem + new_seconds
            session.end_time = now + timedelta(seconds=total_seconds)
            session.remaining_seconds = total_seconds
            session.remaining_minutes = total_seconds // 60
            session.purchased_minutes += minutes
            session.last_accounted_at = now
            session.pause_allowed = session.pause_allowed and pause_allowed
            self._sync_live_session(client_id, session.id, SessionStatus.ACTIVE.value, now)

        elif session and session.status == SessionStatus.PAUSED:
            # Extend existing paused session and reactivate it
            if session.remaining_seconds is not None and session.remaining_seconds > 0:
                old_remaining = session.remaining_seconds
            else:
                old_remaining = (session.remaining_minutes or 0) * 60
            total_seconds = old_remaining + new_seconds

            session.status = SessionStatus.ACTIVE
            session.start_time = now
            session.end_time = now + timedelta(seconds=total_seconds)
            session.remaining_seconds = total_seconds
            session.remaining_minutes = total_seconds // 60
            session.purchased_minutes += minutes
            session.last_accounted_at = now
            session.paused_at = None
            session.pause_allowed = session.pause_allowed and pause_allowed
            self._sync_live_session(client_id, session.id, SessionStatus.ACTIVE.value, now)

        else:
            # Create a brand new session
            session = self.session_repository.create_session(
                client_id=client_id,
                rate_id=rate_id,
                minutes=minutes,
                pause_allowed=pause_allowed,
                commit=False,
            )
            session.remaining_seconds = new_seconds
            session.remaining_minutes = minutes
            session.last_accounted_at = now
            self.db.flush()
            self._sync_live_session(client_id, session.id, SessionStatus.ACTIVE.value, now)

        auth = None
        if client:
            client.status = "ONLINE"
            auth = self._sync_network_auth(client, session.id, "AUTHORIZED", now)

        if commit:
            self.db.commit()
            self.db.refresh(session)
            if client and client.current_ip and authorize:
                try:
                    self.firewall.authorize(client.current_ip, mac=client.mac_address)
                    if auth:
                        auth.applied_state = "AUTHORIZED"
                        auth.last_applied_at = now
                        self.db.commit()
                except Exception:
                    pass

        return session

    def pause_session(self, client_id: int) -> Session:
        client = self.db.query(Client).filter(Client.id == client_id).with_for_update().first()
        live = self.db.query(ClientLiveSession).filter(ClientLiveSession.client_id == client_id).with_for_update().first()
        if not live or live.status != SessionStatus.ACTIVE.value:
            raise ValueError("No active session")

        session = self.db.query(Session).filter(Session.id == live.session_id).with_for_update().first()
        if not session or session.status != SessionStatus.ACTIVE:
            raise ValueError("No active session")

        if not getattr(session, "pause_allowed", True):
            raise ValueError("Pause not allowed for this session package")

        now = get_utc_now()
        # Account for time elapsed since last checkpoint
        last_time = session.last_accounted_at or session.start_time
        elapsed = max(0, int((now - last_time).total_seconds())) if last_time else 0
        rem_sec = max(0, (session.remaining_seconds or 0) - elapsed)
        if rem_sec == 0 and session.end_time:
            rem_sec = max(0, int((session.end_time - now).total_seconds()))

        session.status = SessionStatus.PAUSED
        session.paused_at = now
        session.last_accounted_at = now
        session.remaining_seconds = rem_sec
        session.remaining_minutes = rem_sec // 60

        live.status = SessionStatus.PAUSED.value
        live.updated_at = now

        auth = None
        if client:
            auth = self._sync_network_auth(client, session.id, "BLOCKED", now)

        self.db.commit()

        if client and client.current_ip:
            try:
                self.firewall.remove(client.current_ip, mac=client.mac_address)
                if auth:
                    auth.applied_state = "BLOCKED"
                    auth.last_applied_at = now
                    self.db.commit()
            except Exception:
                pass

        return session

    def resume_session(self, client_id: int) -> Session:
        client = self.db.query(Client).filter(Client.id == client_id).with_for_update().first()
        live = self.db.query(ClientLiveSession).filter(ClientLiveSession.client_id == client_id).with_for_update().first()
        if not live or live.status != SessionStatus.PAUSED.value:
            raise ValueError("No paused session")

        session = self.db.query(Session).filter(Session.id == live.session_id).with_for_update().first()
        if not session or session.status != SessionStatus.PAUSED:
            raise ValueError("No paused session")

        now = get_utc_now()
        if session.remaining_seconds is not None and session.remaining_seconds > 0:
            rem_sec = session.remaining_seconds
        else:
            rem_sec = (session.remaining_minutes or 0) * 60

        session.status = SessionStatus.ACTIVE
        session.start_time = now
        session.end_time = now + timedelta(seconds=rem_sec)
        session.remaining_seconds = rem_sec
        session.remaining_minutes = rem_sec // 60
        session.paused_at = None
        session.last_accounted_at = now

        live.status = SessionStatus.ACTIVE.value
        live.updated_at = now

        auth = None
        if client:
            auth = self._sync_network_auth(client, session.id, "AUTHORIZED", now)

        self.db.commit()

        if client and client.current_ip:
            try:
                self.firewall.authorize(client.current_ip, mac=client.mac_address)
                if auth:
                    auth.applied_state = "AUTHORIZED"
                    auth.last_applied_at = now
                    self.db.commit()
            except Exception:
                pass

        return session