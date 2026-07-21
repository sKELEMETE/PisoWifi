from sqlalchemy import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from utils.time_utils import get_utc_now
from models.session import Session, SessionStatus
from repositories.base_repository import BaseRepository

class SessionRepository(BaseRepository):

    def create(self, session: Session):
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: int):
        return self.db.get(Session, session_id)

    def get_expired_sessions(self):
        stmt = select(Session).where(Session.status == SessionStatus.EXPIRED)
        return self.db.execute(stmt).scalars().all()

    def update(self, session: Session):
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_active_sessions(self):
        stmt = (
            select(Session)
            .options(joinedload(Session.client))
            .where(Session.status == SessionStatus.ACTIVE)
        )

        return self.db.execute(stmt).scalars().all()

    def get_paused_sessions(self):
        stmt = (
            select(Session)
            .where(Session.status == SessionStatus.PAUSED)
        )

        return self.db.execute(stmt).scalars().all()

    def get_active_session_by_client_id(self, client_id: int, for_update: bool = False):
        stmt = (
            select(Session)
            .where(Session.client_id == client_id)
            .where(Session.status == SessionStatus.ACTIVE)
            .order_by(Session.id.desc())
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalars().first()


    def get_paused_session_by_client_id(self, client_id: int, for_update: bool = False):
        stmt = (
            select(Session)
            .where(Session.client_id == client_id)
            .where(Session.status == SessionStatus.PAUSED)
            .order_by(Session.id.desc())
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalars().first()

    def count_active_sessions(self) -> int:
        """Return count of ACTIVE sessions without ORM hydration."""
        from sqlalchemy import func
        result = self.db.execute(
            select(func.count()).select_from(Session).where(Session.status == SessionStatus.ACTIVE)
        )
        return result.scalar_one()

    def create_session(
        self,
        client_id: int,
        rate_id: int,
        minutes: int,
        pause_allowed: bool = True,
        commit: bool = True,
    ):
        now = get_utc_now()

        session = Session(
            client_id=client_id,
            rate_id=rate_id,
            purchased_minutes=minutes,
            remaining_minutes=minutes,
            remaining_seconds=0,
            status=SessionStatus.ACTIVE,
            start_time=now,
            end_time=now + timedelta(minutes=minutes),
            pause_allowed=pause_allowed,
        )

        self.db.add(session)
        if commit:
            self.db.commit()
            self.db.refresh(session)

        return session

