class FirewallService:

    def authorize_client(self, ip: str):
        raise NotImplementedError

    def remove_client(self, ip: str):
        raise NotImplementedError

    def rebuild(self):
        raise NotImplementedError
