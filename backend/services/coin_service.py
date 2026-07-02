from repositories.rate_repository import RateRepository


class CoinService:

    def __init__(self, rate_repository: RateRepository):
        self.rate_repository = rate_repository

    def validate_coin(self, coin_value: int):
        return self.rate_repository.get_by_coin(coin_value)
