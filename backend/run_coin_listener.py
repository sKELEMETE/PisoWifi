from database import SessionLocal

from repositories.rate_repository import RateRepository
from repositories.client_repository import ClientRepository
from repositories.sales_repository import SalesRepository
from repositories.session_repository import SessionRepository

from services.session_service import SessionService
from services.coin_service import CoinService

from coin_serial.coin_listener import CoinListener


db = SessionLocal()

rate_repository = RateRepository(db)
client_repository = ClientRepository(db)
sales_repository = SalesRepository(db)
session_repository = SessionRepository(db)

session_service = SessionService(session_repository)

coin_service = CoinService(
    rate_repository,
    client_repository,
    session_service,
    sales_repository,
)

listener = CoinListener(coin_service)

try:
    listener.run()
finally:
    db.close()
