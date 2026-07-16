from models.sale import Sale
from repositories.base_repository import BaseRepository


class SalesRepository(BaseRepository):

    def create(self, sale: Sale, commit: bool = True):
        self.db.add(sale)
        if commit:
            self.db.commit()
            self.db.refresh(sale)
        return sale
