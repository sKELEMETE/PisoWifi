from sqlalchemy import select

from models.session import Session
from repositories.base_repository import BaseRepository


class SessionRepository(BaseRepository):

    def create(self, session: Session):
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: int):
        return self.db.get(Session, session_id)

    def get_active_by_client(self, client_id: int):
        stmt = (
            select(Session)
            .where(Session.client_id == client_id)
            .where(Session.status == "ACTIVE")
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_paused_by_client(self, client_id: int):
        stmt = (
            select(Session)
            .where(Session.client_id == client_id)
            .where(Session.status == "PAUSED")
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_expired_sessions(self):
        stmt = select(Session).where(Session.status == "EXPIRED")
        return self.db.execute(stmt).scalars().all()

    def update(self, session: Session):
        self.db.commit()
        self.db.refresh(session)
        return session
