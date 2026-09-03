import os
import json
import uuid
import time
import logging
import httpx
import config

logger = logging.getLogger("coin_spool")


class CoinSpool:
    def __init__(self, spool_dir: str | None = None):
        self.spool_dir = spool_dir or os.path.join(config.RUN_DIR, "coin_spool")
        os.makedirs(self.spool_dir, exist_ok=True)

    def _get_filepath(self, event_id: str) -> str:
        return os.path.join(self.spool_dir, f"coin_{event_id}.json")

    def create_event(
        self,
        denomination: int,
        lease_id: str,
        source: str = "serial",
        pulse_count: int | None = None
    ) -> dict:
        """
        Durably creates an event on disk before attempting dispatch.
        Guarantees physical coin events cannot be lost across process crashes.
        """
        event_id = str(uuid.uuid4())
        record = {
            "event_id": event_id,
            "denomination": denomination,
            "lease_id": lease_id,
            "source": source,
            "pulse_count": pulse_count,
            "created_at": time.time(),
            "status": "PENDING",
            "retry_count": 0,
        }

        filepath = self._get_filepath(event_id)
        temp_filepath = f"{filepath}.tmp"
        try:
            with open(temp_filepath, "w") as f:
                json.dump(record, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_filepath, filepath)
            # Fsync directory to ensure directory entry is flushed to flash storage
            try:
                dir_fd = os.open(self.spool_dir, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except Exception:
                pass
            logger.info("Spool record created for event %s (₱%d)", event_id, denomination)
        except Exception as exc:
            logger.error("Failed to write coin spool record: %s", exc)

        return record

    def mark_acknowledged(self, event_id: str):
        filepath = self._get_filepath(event_id)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info("Spool record %s removed after server ACK", event_id)
        except Exception as exc:
            logger.warning("Failed to clean up acknowledged spool record %s: %s", event_id, exc)

    def quarantine_orphaned(self, event_id: str, reason: str = "expired_lease"):
        """Quarantine rejected/orphaned coin records for auditing rather than deleting."""
        filepath = self._get_filepath(event_id)
        quarantine_dir = os.path.join(self.spool_dir, "orphaned")
        try:
            os.makedirs(quarantine_dir, exist_ok=True)
            dest_path = os.path.join(quarantine_dir, f"{event_id}.json")
            if os.path.exists(filepath):
                os.replace(filepath, dest_path)
                try:
                    dir_fd = os.open(quarantine_dir, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                except Exception:
                    pass
                logger.warning("Spool record %s quarantined to %s (reason: %s)", event_id, dest_path, reason)
        except Exception as exc:
            logger.error("Failed to quarantine spool record %s: %s", event_id, exc)

    def dispatch_with_retry(self, event: dict, backend_port: int | None = None, max_retries: int = 5) -> bool:
        """
        Dispatches a spooled event to the backend API with bounded exponential backoff.
        """
        port = backend_port or config.BACKEND_PORT
        url = f"http://127.0.0.1:{port}/api/v1/coin/insert"
        event_id = event["event_id"]
        denomination = event["denomination"]
        lease_id = event["lease_id"]
        source = event.get("source", "serial")
        pulse_count = event.get("pulse_count")

        payload = {
            "event_id": event_id,
            "value": denomination,
            "lease_id": lease_id,
            "source": source,
            "pulse_count": pulse_count,
        }

        delay = 0.2
        for attempt in range(1, max_retries + 1):
            try:
                res = httpx.post(url, params=payload, timeout=5.0)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("success"):
                        logger.info("Server acknowledged coin event %s (attempt %d)", event_id, attempt)
                        self.mark_acknowledged(event_id)
                        return True
                    else:
                        logger.warning("Server rejected coin event %s: %s", event_id, data.get("message"))
                        # If client lease expired or conflict, quarantine record to preserve audit trail
                        if res.status_code == 409 or data.get("message") == "No matching active coin session.":
                            self.quarantine_orphaned(event_id, reason="rejected_409")
                            return False
                elif res.status_code == 409:
                    logger.warning("Server returned 409 for coin event %s: quarantining record", event_id)
                    self.quarantine_orphaned(event_id, reason="conflict_409")
                    return False
                else:
                    logger.error("Server returned status %d for coin event %s: %s", res.status_code, event_id, res.text)
            except Exception as exc:
                logger.warning("Connection error dispatching coin event %s (attempt %d/%d): %s", event_id, attempt, max_retries, exc)

            time.sleep(delay)
            delay = min(delay * 2, 3.0)

        logger.error("Coin event %s remains in write-ahead spool after %d attempts", event_id, max_retries)
        return False

    def reconcile_spool(self, backend_port: int | None = None):
        """
        Recovers and retries any unacknowledged events in the spool on startup or reconnect.
        """
        try:
            if not os.path.exists(self.spool_dir):
                return
            for fname in os.listdir(self.spool_dir):
                if fname.startswith("coin_") and fname.endswith(".json"):
                    fpath = os.path.join(self.spool_dir, fname)
                    try:
                        with open(fpath, "r") as f:
                            event = json.load(f)
                        logger.info("Reconciling spooled coin event %s...", event.get("event_id"))
                        self.dispatch_with_retry(event, backend_port=backend_port, max_retries=3)
                    except Exception as parse_exc:
                        logger.warning("Failed to parse spooled coin file %s: %s", fname, parse_exc)
        except Exception as exc:
            logger.error("Error during coin spool reconciliation: %s", exc)
