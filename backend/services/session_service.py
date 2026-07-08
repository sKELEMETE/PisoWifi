from repositories.session_repository import SessionRepository


class SessionService:

    def __init__(self, session_repository: SessionRepository):
        self.session_repository = session_repository

    def create_or_extend_session(
        self,
        client_id: int,
        rate_id: int,
        minutes: int,
    ):
        session = self.session_repository.get_active_session_by_client_id(client_id)

        if session:
            session.remaining_minutes += minutes
            session.purchased_minutes += minutes

            self.session_repository.db.commit()
            self.session_repository.db.refresh(session)

            return session

        return self.session_repository.create_session(
            client_id=client_id,
            rate_id=rate_id,
            minutes=minutes,
        )
