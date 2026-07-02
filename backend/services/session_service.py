from repositories.session_repository import SessionRepository


class SessionService:

    def __init__(self, repository: SessionRepository):
        self.repository = repository

    def create_session(self):
        raise NotImplementedError

    def extend_session(self):
        raise NotImplementedError

    def pause_session(self):
        raise NotImplementedError

    def resume_session(self):
        raise NotImplementedError

    def expire_session(self):
        raise NotImplementedError

    def restore_session(self):
        raise NotImplementedError
