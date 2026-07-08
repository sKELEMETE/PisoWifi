import threading
import time

from database import SessionLocal
from repositories.rate_repository import RateRepository
from services.coin_service import CoinService
from coin_serial.coin_listener import CoinListener

db = SessionLocal()

rate_repository = RateRepository(db)
coin_service = CoinService(rate_repository)

listener = CoinListener(coin_service)

thread = threading.Thread(
    target=listener.run,
    daemon=True
)

thread.start()

print("Listening...")

try:
    while True:
        if listener.is_connected():
            print("STATUS : CONNECTED")
        else:
            print("STATUS : DISCONNECTED")

        time.sleep(5)

except KeyboardInterrupt:
    print("\nStopping...")
    db.close()
