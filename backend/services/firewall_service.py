import subprocess
import logging
from services.bandwidth_service import BandwidthService

logger = logging.getLogger(__name__)

_bandwidth = BandwidthService()


class FirewallService:

    def _run(self, command):
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

    def authorize(self, ip: str):
        logger.info("========== AUTHORIZE ==========")
        logger.info("IP = %s", ip)


        commands = [
            [
                "/usr/sbin/nft",
                "add",
                "element",
                "inet",
                "pisowifi",
                "authenticated_clients",
                "{",
                ip,
                "}",
            ],
            [
                "/usr/sbin/nft",
                "add",
                "element",
                "ip",
                "nat",
                "authenticated_clients",
                "{",
                ip,
                "}",
            ],
        ]

        for cmd in commands:
            logger.info(cmd)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            logger.info("Return=%s", result.returncode)
            logger.info("stdout=%s", result.stdout)
            logger.info("stderr=%s", result.stderr)

        # Apply per-client bandwidth limit
        try:
            _bandwidth.add_client(ip)
        except Exception as exc:
            logger.warning("Bandwidth limit failed for %s: %s", ip, exc)

    def remove(self, ip: str):
        logger.info("Removing %s", ip)

        commands = [
            [
                "/usr/sbin/nft",
                "delete",
                "element",
                "inet",
                "pisowifi",
                "authenticated_clients",
                "{",
                ip,
                "}",
            ],
            [
                "/usr/sbin/nft",
                "delete",
                "element",
                "ip",
                "nat",
                "authenticated_clients",
                "{",
                ip,
                "}",
            ],
        ]

        for cmd in commands:
            try:
                self._run(cmd)
            except RuntimeError:
                pass

        # Remove per-client bandwidth shaping
        try:
            _bandwidth.remove_client(ip)
        except Exception as exc:
            logger.warning("Bandwidth remove failed for %s: %s", ip, exc)

    def flush(self):
        logger.info("Flushing firewall")

        commands = [
            [
                "/usr/sbin/nft",
                "flush",
                "set",
                "inet",
                "pisowifi",
                "authenticated_clients",
            ],
            [
                "/usr/sbin/nft",
                "flush",
                "set",
                "ip",
                "nat",
                "authenticated_clients",
            ],
        ]

        for cmd in commands:
            self._run(cmd)

    def rebuild(self):
        pass
