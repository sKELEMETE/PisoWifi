import subprocess
import logging

from config import NFT_TABLE_NAME, NFT_SET_NAME

logger = logging.getLogger(__name__)


class FirewallService:
    """
    Production Firewall Service.

    Responsible for modifying only the authenticated
    nftables set. Firewall rules themselves never change.
    """

    def _run(self, command: list[str]):
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

    def authorize(self, ip: str):
        logger.info("Authorizing %s", ip)

        self._run([
            "sudo",
            "nft",
            "add",
            "element",
            "inet",
            NFT_TABLE_NAME,
            NFT_SET_NAME,
            "{",
            ip,
            "}",
        ])

    def remove(self, ip: str):
        logger.info("Removing %s", ip)

        self._run([
            "sudo",
            "nft",
            "delete",
            "element",
            "inet",
            NFT_TABLE_NAME,
            NFT_SET_NAME,
            "{",
            ip,
            "}",
        ])

    def flush(self):
        logger.info("Flushing authenticated clients")

        self._run([
            "sudo",
            "nft",
            "flush",
            "set",
            "inet",
            NFT_TABLE_NAME,
            NFT_SET_NAME,
        ])

    def rebuild(self):
        """
        Reserved for future use.
        Recovery currently performs rebuilding.
        """
        pass
