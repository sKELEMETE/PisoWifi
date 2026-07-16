import logging

logger = logging.getLogger(__name__)


class StartupSequence:
    """
    Coordinates backend startup recovery.
    """

    def __init__(
        self,
        database_recovery,
        power_recovery,
        session_recovery,
        firewall_recovery,
    ):
        self.database_recovery = database_recovery
        self.power_recovery = power_recovery
        self.session_recovery = session_recovery
        self.firewall_recovery = firewall_recovery

    def _reconcile_pending_coins(self):
        import glob
        import os
        import json
        from database import SessionLocal
        from repositories.rate_repository import RateRepository
        from repositories.client_repository import ClientRepository
        from repositories.sales_repository import SalesRepository
        from repositories.session_repository import SessionRepository
        from services.session_service import SessionService
        from services.coin_service import CoinService

        pattern = "/opt/pisowifi/run/session_coins_*.json"
        files = glob.glob(pattern)
        if not files:
            return

        logger.info("Found %d pending coin session file(s). Reconciling...", len(files))
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

            for path in files:
                filename = os.path.basename(path)
                mac = filename[14:-5]
                try:
                    with open(path, "r") as f:
                        coins = json.load(f)
                    if coins:
                        logger.info("Reconciling %d coin(s) for MAC: %s", len(coins), mac)
                        coin_service.process_coins_bulk(mac, coins, authorize=True)
                except Exception as exc:
                    logger.error("Failed to reconcile file %s: %s", filename, exc)
                finally:
                    try:
                        os.remove(path)
                    except FileNotFoundError:
                        pass
        finally:
            db.close()

    def run(self):
        logger.info("========== STARTUP ==========")

        logger.info("1. Waiting for database...")
        self.database_recovery.wait_until_available()

        logger.info("1.5. Reconciling pending coins...")
        try:
            self._reconcile_pending_coins()
        except Exception as exc:
            logger.error("Pending coin reconciliation failed: %s", exc)

        logger.info("2. Running power recovery...")
        paused = self.power_recovery.recover()

        logger.info("Paused %s active session(s).", paused)

        logger.info("3. Recovering sessions...")
        sessions = self.session_recovery.recover()

        logger.info(
            "Recovered %s active, %s paused session(s).",
            len(sessions["active"]),
            len(sessions["paused"]),
        )

        logger.info("4. Rebuilding firewall...")
        restored = self.firewall_recovery.rebuild()

        logger.info(
            "Restored %s firewall authorization(s).",
            restored,
        )

        logger.info("========== SYSTEM READY ==========")
