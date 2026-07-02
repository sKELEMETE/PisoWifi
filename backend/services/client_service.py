from repositories.client_repository import ClientRepository
from models.client import Client


class ClientService:

    def __init__(self, repository: ClientRepository):
        self.repository = repository

    def register_client(
        self,
        mac_address: str,
        current_ip: str,
        hostname: str | None = None,
    ) -> Client:

        client = self.repository.get_by_mac(mac_address)

        if client:
            client.current_ip = current_ip
            client.hostname = hostname
            client.status = "ONLINE"

            return self.repository.update(client)

        client = Client(
            mac_address=mac_address,
            current_ip=current_ip,
            hostname=hostname,
            status="ONLINE",
        )

        return self.repository.create(client)

    def update_ip(self, client: Client, ip: str):
        client.current_ip = ip
        return self.repository.update(client)

    def update_hostname(self, client: Client, hostname: str):
        client.hostname = hostname
        return self.repository.update(client)

    def update_status(self, client: Client, status: str):
        return self.repository.update_status(client, status)

