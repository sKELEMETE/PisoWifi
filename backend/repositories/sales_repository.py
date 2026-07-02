from models.sale import Sale
from repositories.base_repository import BaseRepository


class SalesRepository(BaseRepository):

    def create(self, sale: Sale):
        self.db.add(sale)
        self.db.commit()
        self.db.refresh(sale)
        return sale
