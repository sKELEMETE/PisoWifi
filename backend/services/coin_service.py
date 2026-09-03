from repositories.sales_repository import SalesRepository
from models.sale import Sale, PaymentMethod

class CoinService:
    def __init__(self, rate_repository, client_repository, session_service, sale_repository):
        self.rate_repository = rate_repository
        self.client_repository = client_repository
        self.session_service = session_service
        self.sale_repository = sale_repository

    def validate_coin(self, coin_value):
        return self.rate_repository.get_by_coin(coin_value)

    def process_coin(self, mac_address, coin_value, authorize: bool = True):
        rate = self.rate_repository.get_by_coin(coin_value)
        if rate is None:
            return False

        client = self.client_repository.get_or_create(mac_address)
        db = self.sale_repository.db
        try:
            session = self.session_service.create_or_extend_session(
                client.id,
                rate.id,
                rate.minutes,
                authorize=False,
                commit=False,
            )

            sale = Sale(
                session=session,
                rate_id=rate.id,
                amount=coin_value,
                minutes=rate.minutes,
                payment_method=PaymentMethod.COIN,
            )
            self.sale_repository.create(sale, commit=False)
            db.commit()
            db.refresh(session)

            if client.current_ip and authorize:
                self.session_service.firewall.authorize(client.current_ip, mac=client.mac_address)

            return session
        except Exception as exc:
            db.rollback()
            raise exc

    def process_coins_bulk(self, mac_address: str, coins: list[int], authorize: bool = True, commit: bool = True):
        if not coins:
            return None

        total_amount = sum(coins)
        from config import get_minutes_and_pause_eligibility
        total_minutes, pause_allowed = get_minutes_and_pause_eligibility(total_amount)

        # Retrieve rate package matching total amount, fallback to 20 or 1
        rate = self.rate_repository.get_by_coin(total_amount)
        if rate is None:
            rate = self.rate_repository.get_by_coin(20) or self.rate_repository.get_by_coin(1)

        if rate is None:
            raise RuntimeError("No rates configured in database.")

        client = self.client_repository.get_or_create(mac_address)
        db = self.sale_repository.db
        try:
            session = self.session_service.create_or_extend_session(
                client.id,
                rate.id,
                total_minutes,
                authorize=False,
                pause_allowed=pause_allowed,
                commit=False,
            )

            # Insert Sale records for each coin (minutes=0 to prevent double-crediting)
            for coin_val in coins:
                coin_rate = self.rate_repository.get_by_coin(coin_val)
                rate_id = coin_rate.id if coin_rate else rate.id
                sale = Sale(
                    session=session,
                    rate_id=rate_id,
                    amount=coin_val,
                    minutes=0,
                    payment_method=PaymentMethod.COIN,
                )
                self.sale_repository.create(sale, commit=False)

            if commit:
                db.commit()
                db.refresh(session)
                if client.current_ip and authorize:
                    self.session_service.firewall.authorize(client.current_ip, mac=client.mac_address)
            return session
        except Exception as exc:
            if commit:
                db.rollback()
            raise exc
