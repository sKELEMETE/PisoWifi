from sqlalchemy import select

from models.client import Client
from repositories.base_repository import BaseRepository


class ClientRepository(BaseRepository):

    def create(self, client: Client) -> Client:
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def get_by_id(self, client_id: int):
        return self.db.get(Client, client_id)

    def get_by_mac(self, mac_address: str):
        stmt = select(Client).where(Client.mac_address == mac_address)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_ip(self, ip: str):
        stmt = select(Client).where(Client.current_ip == ip)
        return self.db.execute(stmt).scalar_one_or_none()

    def update(self, client: Client):
        self.db.commit()
        self.db.refresh(client)
        return client

    def delete(self, client: Client):
        self.db.delete(client)
        self.db.commit()

    def update_status(self, client: Client, status: str):
        client.status = status
        self.db.commit()
        self.db.refresh(client)
        return client
