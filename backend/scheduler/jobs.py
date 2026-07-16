import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func
from database import SessionLocal
from models.session import Session as SessionModel
from models.client import Client
from services.firewall_service import FirewallService
import config

logger = logging.getLogger(__name__)

_last_system_time = None
_last_monotonic_time = None

def expire_sessions():
    global _last_system_time, _last_monotonic_time
    import time

    db = SessionLocal()
    try:
        firewall = FirewallService()
        now = datetime.now()
        current_mono = time.monotonic()

        # Compensate for system clock jumps (e.g. NTP sync) to protect session remaining time
        if _last_system_time is not None and _last_monotonic_time is not None:
            system_diff = (now - _last_system_time).total_seconds()
            monotonic_diff = current_mono - _last_monotonic_time
            if abs(system_diff - monotonic_diff) > 5.0:
                jump_seconds = system_diff - monotonic_diff
                logger.warning("Clock jump of %s seconds detected. Adjusting session end_times...", jump_seconds)
                try:
                    from sqlalchemy import update
                    db.execute(
                        update(SessionModel)
                        .where(SessionModel.status == "ACTIVE")
                        .values(end_time=SessionModel.end_time + timedelta(seconds=jump_seconds))
                    )
                    db.commit()
                except Exception as exc:
                    logger.error("Failed to compensate active session end times for clock jump: %s", exc)

        _last_system_time = now
        _last_monotonic_time = current_mono

        # Expire ACTIVE sessions whose end_time has passed.
        # Single JOIN query to avoid N+1 client lookups.
        expired_active = db.execute(
            select(SessionModel, Client.current_ip)
            .join(Client, Client.id == SessionModel.client_id)
            .where(SessionModel.status == "ACTIVE")
            .where(SessionModel.end_time <= now)
        ).all()

        for session, client_ip in expired_active:
            session.status = "EXPIRED"
            session.remaining_minutes = 0
            if client_ip:
                firewall.remove(client_ip)

        # Expire stale PAUSED sessions:
        #   - sessions with zero remaining seconds (remaining_minutes column holds seconds while paused)
        #   - sessions paused longer than PAUSE_EXPIRATION_DAYS
        stale_cutoff = now - timedelta(days=config.PAUSE_EXPIRATION_DAYS)
        stale_paused = db.execute(
            select(SessionModel, Client.current_ip)
            .join(Client, Client.id == SessionModel.client_id)
            .where(SessionModel.status == "PAUSED")
            .where(
                (SessionModel.remaining_minutes <= 0) |
                (SessionModel.paused_at <= stale_cutoff)
            )
        ).all()

        for session, client_ip in stale_paused:
            session.status = "EXPIRED"
            session.remaining_minutes = 0
            if client_ip:
                firewall.remove(client_ip)

        db.commit()
    except Exception as e:
        logger.error("Session expiration lookup failed: %s", e)
    finally:
        db.close()

def sync_firewall():
    import json
    import subprocess
    from database import SessionLocal
    from models.session import Session as SessionModel
    from models.client import Client
    from services.firewall_service import FirewallService

    db = SessionLocal()
    try:
        firewall = FirewallService()
        # 1. Get active IPs from database
        active_ips = db.execute(
            select(Client.current_ip)
            .join(SessionModel, SessionModel.client_id == Client.id)
            .where(SessionModel.status == "ACTIVE")
        ).scalars().all()
        active_ips = {ip for ip in active_ips if ip}

        # 2. Get actual IPs from nftables sets
        nft_ips = set()
        for family, table, set_name in [("inet", "pisowifi", "authenticated_clients"), ("ip", "nat", "authenticated_clients")]:
            cmd = ["/usr/sbin/nft", "-j", "list", "set", family, table, set_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    for obj in data.get("nftables", []):
                        if "set" in obj and "elem" in obj["set"]:
                            nft_ips.update(obj["set"]["elem"])
                except Exception:
                    pass

        # 3. Remove orphans (IP in nftables but not active in DB)
        orphans = nft_ips - active_ips
        for ip in orphans:
            logger.info("Firewall Auditor: removing orphan IP %s", ip)
            try:
                firewall.remove(ip)
            except Exception as exc:
                logger.error("Firewall Auditor: failed to remove orphan %s: %s", ip, exc)

        # 4. Restore missing (IP active in DB but missing from nftables)
        missing = active_ips - nft_ips
        for ip in missing:
            logger.info("Firewall Auditor: authorizing missing IP %s", ip)
            try:
                firewall.authorize(ip)
            except Exception as exc:
                logger.error("Firewall Auditor: failed to restore missing %s: %s", ip, exc)

    except Exception as e:
        logger.error("Firewall Auditor sync failed: %s", e)
    finally:
        db.close()

def backup(): pass