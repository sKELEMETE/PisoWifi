import logging
import config

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
        from database import SessionLocal
        from models.coin_reservation import CoinReservation, PendingCoin
        from repositories.rate_repository import RateRepository
        from repositories.client_repository import ClientRepository
        from repositories.sales_repository import SalesRepository
        from repositories.session_repository import SessionRepository
        from services.session_service import SessionService
        from services.coin_service import CoinService
        from services.firewall_service import FirewallService

        db = SessionLocal()
        try:
            pending_macs = [r[0] for r in db.query(PendingCoin.mac).distinct().all()]
            if not pending_macs:
                return

            logger.info("Found %d MAC(s) with pending coins on startup. Reconciling...", len(pending_macs))
            
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

            for mac in pending_macs:
                records = db.query(PendingCoin).filter(PendingCoin.mac == mac).all()
                coins = [r.amount for r in records]
                if coins:
                    logger.info("Startup Recovery: Reconciling %d coin(s) for client %s.", len(coins), mac)
                    try:
                        coin_service.process_coins_bulk(mac, coins, authorize=True, commit=False)
                        db.query(PendingCoin).filter(PendingCoin.mac == mac).delete()
                        db.query(CoinReservation).filter(CoinReservation.mac == mac).delete()
                        db.commit()
                        client = client_repository.get_by_mac(mac)
                        if client and client.current_ip:
                            FirewallService().authorize(client.current_ip)
                    except Exception as exc:
                        db.rollback()
                        logger.error("Startup Recovery: Failed to reconcile coins for %s: %s", mac, exc)
        except Exception as exc:
            logger.error("Startup Recovery: DB error during coin reconciliation: %s", exc)
        finally:
            db.close()

    def _seed_default_rates(self):
        from database import SessionLocal
        from models.rate import Rate
        import config

        db = SessionLocal()
        try:
            count = db.query(Rate).count()
            if count == 0:
                logger.info("Rates table is empty. Seeding default rates...")
                voucher_rate = Rate(coin_value=0, minutes=0, enabled=True)
                db.add(voucher_rate)
                for coin, (minutes, _) in config.PRICING_TABLE.items():
                    rate = Rate(coin_value=coin, minutes=minutes, enabled=True)
                    db.add(rate)
                db.commit()
                logger.info("Successfully seeded default rates.")
        except Exception as exc:
            db.rollback()
            logger.error("Failed to seed default rates: %s", exc)
        finally:
            db.close()

    def run(self):
        logger.info("========== STARTUP ==========")

        logger.info("1. Waiting for database...")
        self.database_recovery.wait_until_available()

        logger.info("1.2. Seeding default rates...")
        try:
            self._seed_default_rates()
        except Exception as exc:
            logger.error("Rates seeding failed: %s", exc)

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
