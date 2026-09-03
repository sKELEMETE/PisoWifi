import logging
from datetime import datetime
from sqlalchemy.orm import Session
from utils.time_utils import get_utc_now
from models.coin_reservation import CoinReservation, PendingCoin
from models.coin_event import CoinEvent, CoinEventStatus
from models.sale import Sale, PaymentMethod
from repositories.rate_repository import RateRepository
from repositories.client_repository import ClientRepository
from repositories.session_repository import SessionRepository
from services.session_service import SessionService
from services.firewall_service import FirewallService

logger = logging.getLogger("coin_settlement")


class CoinSettlementService:
    def __init__(self, db: Session, session_service: SessionService | None = None, firewall_service: FirewallService | None = None):
        self.db = db
        self.rate_repo = RateRepository(db)
        self.client_repo = ClientRepository(db)
        self.session_repo = SessionRepository(db)
        self.firewall = firewall_service or FirewallService()
        self.session_service = session_service or SessionService(self.session_repo, firewall_service=self.firewall)

    def finalize_lease(self, lease_id: str | None = None, mac: str | None = None, authorize: bool = True) -> dict:
        """
        Atomically and idempotently finalizes coin reservations and claims unprocessed coin events.
        Guarantees:
        1. Row-locking prevents concurrent double settlement.
        2. Coin events are claimed exactly once.
        3. Successive calls with the same lease return already-finalized state with 0 additional credit.
        """
        now = get_utc_now()

        # Step 1: Lock reservation row
        query = self.db.query(CoinReservation).with_for_update()
        if lease_id:
            reservation = query.filter(CoinReservation.lease_id == lease_id).first()
        elif mac:
            reservation = query.filter(CoinReservation.mac == mac).first()
        else:
            return {"status": "error", "message": "Neither lease_id nor mac provided."}

        target_mac = reservation.mac if reservation else mac
        if not target_mac and lease_id:
            # Check historical CoinEvent for lease_id to recognize already finalized leases
            ev = self.db.query(CoinEvent).filter(CoinEvent.lease_id == lease_id).first()
            if ev:
                target_mac = ev.mac

        if not target_mac:
            return {"status": "not_found", "total_amount": 0, "total_minutes": 0}

        masked_mac = f"**:**:**:**:{target_mac[-5:]}" if len(target_mac) >= 5 else target_mac

        # Step 2: Atomically claim unprocessed CoinEvent rows
        if lease_id:
            event_filter = (CoinEvent.lease_id == lease_id)
        else:
            event_filter = (CoinEvent.mac == target_mac)

        unprocessed_events = self.db.query(CoinEvent).filter(
            event_filter,
            CoinEvent.status == CoinEventStatus.RECEIVED.value
        ).all()
        claimed_ids = [e.id for e in unprocessed_events]

        coins = []
        if claimed_ids:
            claimed_count = self.db.query(CoinEvent).filter(
                CoinEvent.id.in_(claimed_ids),
                CoinEvent.status == CoinEventStatus.RECEIVED.value
            ).update(
                {"status": CoinEventStatus.PROCESSED.value, "processed_at": now},
                synchronize_session=False
            )
            if claimed_count > 0:
                coins = [e.denomination for e in unprocessed_events]

        pending_records = self.db.query(PendingCoin).with_for_update().filter(
            PendingCoin.mac == target_mac
        ).all()
        if not coins and pending_records:
            coins = [p.amount for p in pending_records]
            for p in pending_records:
                self.db.delete(p)

        total_amount = sum(coins)

        # If no unprocessed events and no active reservation, it was already finalized!
        if not reservation and total_amount == 0:
            logger.info("Lease %s for %s already finalized. Idempotent return.", lease_id, masked_mac)
            return {
                "status": "already_finalized",
                "mac": target_mac,
                "total_amount": 0,
                "total_minutes": 0,
            }

        client = self.client_repo.get_by_mac(target_mac)
        if not client:
            client = self.client_repo.get_or_create(target_mac)

        session_id = None
        total_minutes = 0

        if total_amount > 0:
            # Delegate monetary settlement to canonical CoinService
            import api.v1.coin as coin_api_module
            coin_service = coin_api_module._coin_service(self.db)
            session = coin_service.process_coins_bulk(target_mac, coins, authorize=False, commit=False)
            if session:
                session_id = session.id
                total_minutes = getattr(session, "purchased_minutes", 0)

        if reservation:
            self.db.delete(reservation)

        # Step 8: Commit transaction atomically
        self.db.commit()

        # Step 9: Reconcile network authorization post-commit
        if authorize and total_amount > 0 and client and client.current_ip:
            try:
                self.firewall.authorize(client.current_ip, mac=target_mac)
            except Exception as exc:
                logger.error("Firewall authorization failed after coin settlement for %s: %s", masked_mac, exc)

        logger.info(
            "Finalized lease %s for %s: total_amount=₱%d, total_minutes=%dm, session_id=%s",
            lease_id, masked_mac, total_amount, total_minutes, session_id
        )

        return {
            "status": "finalized",
            "mac": target_mac,
            "total_amount": total_amount,
            "total_minutes": total_minutes,
            "session_id": session_id,
        }
