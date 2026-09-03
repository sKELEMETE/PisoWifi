import logging
from datetime import datetime
from sqlalchemy.orm import Session
from utils.time_utils import get_utc_now
from models.network_authorization import NetworkAuthorization, NetworkAuthState
from services.firewall_service import FirewallService

logger = logging.getLogger("firewall_reconciler")


class FirewallReconciler:
    def __init__(self, firewall_service: FirewallService | None = None):
        self.firewall = firewall_service or FirewallService()

    def reconcile_once(self, db: Session) -> dict:
        """
        Continuously reconciles database desired authorization state with active kernel nftables state.
        Computes delta, applies atomic batch corrections, and reports drift metrics.
        """
        now = get_utc_now()
        records = db.query(NetworkAuthorization).all()

        # Build expected authorized set from database
        desired_authorized_pairs: set[tuple[str, str]] = set()
        record_map_by_pair: dict[tuple[str, str], NetworkAuthorization] = {}
        record_map_by_ip: dict[str, NetworkAuthorization] = {}

        for rec in records:
            if rec.ip_address:
                norm_pair = (rec.ip_address.strip(), rec.mac_address.strip().lower())
                record_map_by_pair[norm_pair] = rec
                record_map_by_ip[rec.ip_address.strip()] = rec
                if rec.desired_state == NetworkAuthState.AUTHORIZED.value:
                    desired_authorized_pairs.add(norm_pair)

        # Inspect current running kernel state
        active_kernel_pairs = self.firewall.get_active_kernel_elements()

        # Compute discrepancies
        missing_in_kernel = desired_authorized_pairs - active_kernel_pairs
        stale_in_kernel = active_kernel_pairs - desired_authorized_pairs

        false_deny_count = len(missing_in_kernel)
        stale_allow_count = len(stale_in_kernel)

        to_add = list(missing_in_kernel)
        to_remove = list(stale_in_kernel)

        if to_add or to_remove:
            logger.info(
                "Firewall drift detected: adding %d missing pair(s), removing %d stale pair(s)",
                len(to_add), len(to_remove)
            )
            success = self.firewall.apply_batch(to_add, to_remove)
            if success:
                for pair in to_add:
                    rec = record_map_by_pair.get(pair)
                    if rec:
                        rec.applied_state = NetworkAuthState.AUTHORIZED.value
                        rec.last_applied_at = now
                        rec.failure_count = 0
                        rec.last_error = None
                for pair in to_remove:
                    rec = record_map_by_pair.get(pair) or record_map_by_ip.get(pair[0])
                    if rec and rec.desired_state != NetworkAuthState.AUTHORIZED.value:
                        rec.applied_state = NetworkAuthState.BLOCKED.value
                        rec.last_applied_at = now
                        rec.failure_count = 0
                        rec.last_error = None
            else:
                logger.error("Firewall batch reconciliation failed")
                for pair in to_add:
                    rec = record_map_by_pair.get(pair)
                    if rec:
                        rec.failure_count += 1
                        rec.last_error = "Firewall batch apply failed"

        # Check for DB records where desired != applied
        out_of_sync_count = 0
        for rec in records:
            if rec.desired_state != rec.applied_state:
                out_of_sync_count += 1

        db.commit()

        metrics = {
            "out_of_sync_count": out_of_sync_count,
            "stale_allow_count": stale_allow_count,
            "false_deny_count": false_deny_count,
            "timestamp": now.isoformat(),
        }

        if out_of_sync_count > 0 or stale_allow_count > 0 or false_deny_count > 0:
            logger.warning("Firewall reconciler completed with non-zero drift: %s", metrics)
        else:
            logger.debug("Firewall state perfectly in sync.")

        return metrics
