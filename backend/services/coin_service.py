from repositories.sales_repository import SalesRepository
from models.sale import Sale, PaymentMethod

class CoinService:

    def __init__(
        self,
        rate_repository,
        client_repository,
        session_service,
        sale_repository=None,
    ):
        self.rate_repository = rate_repository
        self.client_repository = client_repository
        self.session_service = session_service
        self.sale_repository = sale_repository or SalesRepository()

    def validate_coin(self, coin_value):
        return self.rate_repository.get_by_coin(coin_value)

    def process_coin(self, mac_address, coin_value):
        print(f"Processing ₱{coin_value}")

        rate = self.rate_repository.get_by_coin(coin_value)

        if rate is None:
            print(f"No rate configured for ₱{coin_value}")
            return False

        client = self.client_repository.get_or_create(mac_address)

        session = self.session_service.create_or_extend_session(
            client.id,
            rate.id,
            rate.minutes,
        )

        sale = Sale(
            session_id=session.id,
            rate_id=rate.id,
            amount=coin_value,
            minutes=rate.minutes,
            payment_method=PaymentMethod.COIN,
        )

        self.sale_repository.create(sale)

        print(
            f"Added {rate.minutes} minutes to {mac_address}"
        )

        return session
