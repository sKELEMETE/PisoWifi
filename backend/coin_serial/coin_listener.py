import logging
import fcntl
from database import SessionLocal
from coin_serial.debounce import Debouncer
from coin_serial.packet_validator import validate_packet
from coin_serial.serial_manager import SerialManager
from repositories.rate_repository import RateRepository
from repositories.client_repository import ClientRepository
from repositories.sales_repository import SalesRepository
from repositories.session_repository import SessionRepository
from services.session_service import SessionService
from services.coin_service import CoinService

logger = logging.getLogger(__name__)

class CoinListener:
    def __init__(self):
        self.manager = SerialManager()
        self.debounce = Debouncer()

    def get_active_mac(self):
        try:
            with open("/tmp/active_mac.txt", "r") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                mac = f.read().strip()
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return mac
        except FileNotFoundError:
            return None

    def update_pending_balance(self, value):
        current = 0
        try:
            with open("/tmp/pending_coin.txt", "r+") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                content = f.read().strip()
                if content:
                    current = int(content)
                f.seek(0)
                f.write(str(current + value))
                f.truncate()
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except FileNotFoundError:
            with open("/tmp/pending_coin.txt", "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(str(value))
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def process_coin(self, mac, value):
        self.update_pending_balance(value)
        try:
            import os
            os.utime("/tmp/active_mac.txt", None)
        except Exception:
            pass

        import json
        import os
        coins_file = f"/tmp/session_coins_{mac}.json"
        coins = []
        try:
            if os.path.exists(coins_file):
                with open(coins_file, "r") as f:
                    coins = json.load(f)
        except Exception:
            pass
        
        coins.append(value)
        try:
            with open(coins_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(coins, f)
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass


    def run(self):
        self.manager.connect()
        logger.info("Coin listener started.")
        while True:
            packet = self.manager.read()
            if packet is None:
                continue
            if not self.debounce.allow(packet):
                continue
            value = validate_packet(packet)
            if value is None:
                continue
            mac = self.get_active_mac()
            if mac:
                self.process_coin(mac, value)