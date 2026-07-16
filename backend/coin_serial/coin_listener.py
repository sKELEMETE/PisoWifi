import json
import logging
import fcntl
import os
import time
import threading

from coin_serial.debounce import Debouncer
from coin_serial.packet_validator import validate_packet
from coin_serial.serial_manager import SerialManager

logger = logging.getLogger(__name__)

ACTIVE_MAC_FILE = "/opt/pisowifi/run/active_mac.txt"
PENDING_COIN_FILE = "/opt/pisowifi/run/pending_coin.txt"
RESERVATION_TIMEOUT = 30  # seconds of inactivity before auto-finalize and release


class CoinListener:
    def __init__(self):
        self.manager = SerialManager()
        self.debounce = Debouncer()

    # ─────────────────────────────────────────────────────────────
    # State readers
    # ─────────────────────────────────────────────────────────────

    def get_active_mac(self) -> str | None:
        try:
            with open(ACTIVE_MAC_FILE, "r") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                mac = f.read().strip()
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return mac if mac else None
        except FileNotFoundError:
            return None

    def is_slot_accepting(self) -> bool:
        """Return True only when active_mac.txt exists AND mtime is < RESERVATION_TIMEOUT seconds ago."""
        try:
            age = time.time() - os.path.getmtime(ACTIVE_MAC_FILE)
            return age < RESERVATION_TIMEOUT
        except FileNotFoundError:
            return False

    # ─────────────────────────────────────────────────────────────
    # Coin accumulation
    # ─────────────────────────────────────────────────────────────

    def update_pending_balance(self, value: int):
        current = 0
        try:
            with open(PENDING_COIN_FILE, "r+") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                content = f.read().strip()
                if content:
                    current = int(content)
                f.seek(0)
                f.write(str(current + value))
                f.truncate()
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except FileNotFoundError:
            with open(PENDING_COIN_FILE, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(str(value))
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def process_coin(self, mac: str, value: int):
        self.update_pending_balance(value)
        # Touch active_mac.txt to extend the 30-second reservation window
        try:
            os.utime(ACTIVE_MAC_FILE, None)
        except Exception:
            pass

        coins_file = f"/opt/pisowifi/run/session_coins_{mac}.json"
        coins: list[int] = []
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

    # ─────────────────────────────────────────────────────────────
    # Watchdog: auto-finalize + release after 30 s of inactivity
    # ─────────────────────────────────────────────────────────────

    def _finalize_and_release(self, mac: str):
        """
        Called by the watchdog when the 30-second reservation times out.

        Two cases:
          1. No coins inserted → reservation expired silently. Just clean up.
          2. Coins were inserted → finalize purchase (create/extend session,
             authorize internet) THEN clean up.

        Uses a fresh DB session so this can run safely from a background thread.
        """
        coins_file = f"/opt/pisowifi/run/session_coins_{mac}.json"
        coins: list[int] = []

        try:
            if os.path.exists(coins_file):
                with open(coins_file, "r") as f:
                    coins = json.load(f)
        except Exception:
            pass

        if coins:
            logger.info(
                "Watchdog: reservation timed out for %s with %d coin(s). Finalizing.",
                mac, len(coins),
            )
            try:
                # Import here to avoid circular imports at module load time
                from database import SessionLocal
                from repositories.rate_repository import RateRepository
                from repositories.client_repository import ClientRepository
                from repositories.sales_repository import SalesRepository
                from repositories.session_repository import SessionRepository
                from services.session_service import SessionService
                from services.coin_service import CoinService

                db = SessionLocal()
                try:
                    rate_repository = RateRepository(db)
                    client_repository = ClientRepository(db)
                    sales_repository = SalesRepository(db)
                    session_repository = SessionRepository(db)
                    session_service = SessionService(session_repository)
                    coin_service = CoinService(
                        rate_repository=rate_repository,
                        client_repository=client_repository,
                        session_service=session_service,
                        sale_repository=sales_repository,
                    )
                    coin_service.process_coins_bulk(mac, coins, authorize=True)
                    logger.info("Watchdog: session finalized for %s.", mac)
                except Exception as exc:
                    logger.error("Watchdog: failed to finalize session for %s: %s", mac, exc)
                finally:
                    db.close()
            except Exception as exc:
                logger.error("Watchdog: DB error during finalize: %s", exc)
        else:
            logger.info(
                "Watchdog: reservation timed out for %s with no coins. Releasing.",
                mac,
            )

        # Clean up reservation files regardless of outcome
        for path in (ACTIVE_MAC_FILE, PENDING_COIN_FILE, coins_file):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

        logger.info("Watchdog: slot released for %s.", mac)

    def _watchdog(self):
        """
        Background thread.
        Polls every second. When active_mac.txt mtime >= RESERVATION_TIMEOUT,
        calls _finalize_and_release() then cleans up files.
        """
        while True:
            time.sleep(1)
            try:
                if not os.path.exists(ACTIVE_MAC_FILE):
                    continue
                age = time.time() - os.path.getmtime(ACTIVE_MAC_FILE)
                if age >= RESERVATION_TIMEOUT:
                    mac = self.get_active_mac()
                    if mac:
                        self._finalize_and_release(mac)
                    else:
                        # File exists but is empty — just clean up
                        for path in (ACTIVE_MAC_FILE, PENDING_COIN_FILE):
                            try:
                                os.remove(path)
                            except FileNotFoundError:
                                pass
            except Exception as exc:
                logger.warning("Watchdog error: %s", exc)

    # ─────────────────────────────────────────────────────────────
    # Main loop
    # ─────────────────────────────────────────────────────────────

    def run(self):
        self.manager.connect()
        logger.info("Coin listener started.")

        watchdog_thread = threading.Thread(target=self._watchdog, daemon=True)
        watchdog_thread.start()
        logger.info("Coin slot watchdog started (timeout=%ds).", RESERVATION_TIMEOUT)

        while True:
            packet = self.manager.read()
            if packet is None:
                continue
            if not self.debounce.allow(packet):
                continue
            value = validate_packet(packet)
            if value is None:
                continue
            # Only process coins when the slot is actively reserved
            if not self.is_slot_accepting():
                logger.debug("Coin received but slot is not active — ignoring.")
                continue
            mac = self.get_active_mac()
            if mac:
                self.process_coin(mac, value)