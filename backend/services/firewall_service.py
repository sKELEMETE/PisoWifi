import subprocess
import logging
import config
from abc import ABC, abstractmethod
from services.bandwidth_service import BandwidthService

logger = logging.getLogger(__name__)

_bandwidth = BandwidthService()


class FirewallDriver(ABC):

    @abstractmethod
    def authorize(self, ip: str) -> None:
        pass

    @abstractmethod
    def remove(self, ip: str) -> None:
        pass

    @abstractmethod
    def flush(self) -> None:
        pass


class NftablesFirewallDriver(FirewallDriver):

    def _run(self, command):
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

    def authorize(self, ip: str) -> None:
        logger.info("========== AUTHORIZE (nftables) ==========")
        logger.info("IP = %s", ip)

        commands = [
            [
                config.PATH_NFT,
                "add",
                "element",
                "inet",
                config.NFT_TABLE_NAME,
                config.NFT_SET_NAME,
                "{",
                ip,
                "}",
            ],
            [
                config.PATH_NFT,
                "add",
                "element",
                "ip",
                "nat",
                config.NFT_SET_NAME,
                "{",
                ip,
                "}",
            ],
        ]

        for cmd in commands:
            logger.info("Executing firewall command: %s", cmd)
            self._run(cmd)


    def remove(self, ip: str) -> None:
        logger.info("Removing %s (nftables)", ip)

        commands = [
            [
                config.PATH_NFT,
                "delete",
                "element",
                "inet",
                config.NFT_TABLE_NAME,
                config.NFT_SET_NAME,
                "{",
                ip,
                "}",
            ],
            [
                config.PATH_NFT,
                "delete",
                "element",
                "ip",
                "nat",
                config.NFT_SET_NAME,
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

    def flush(self) -> None:
        logger.info("Flushing firewall (nftables)")

        commands = [
            [
                config.PATH_NFT,
                "flush",
                "set",
                "inet",
                config.NFT_TABLE_NAME,
                config.NFT_SET_NAME,
            ],
            [
                config.PATH_NFT,
                "flush",
                "set",
                "ip",
                "nat",
                config.NFT_SET_NAME,
            ],
        ]

        for cmd in commands:
            self._run(cmd)


class MockFirewallDriver(FirewallDriver):

    def __init__(self):
        self.active_ips = set()

    def authorize(self, ip: str) -> None:
        logger.info("========== AUTHORIZE (mock) ==========")
        logger.info("IP = %s added to allowed set", ip)
        self.active_ips.add(ip)

    def remove(self, ip: str) -> None:
        logger.info("Removing %s (mock)", ip)
        self.active_ips.discard(ip)

    def flush(self) -> None:
        logger.info("Flushing firewall (mock)")
        self.active_ips.clear()


class FirewallService:

    def __init__(self):
        driver_name = config.FIREWALL_DRIVER.lower()
        if driver_name == "nftables":
            self.driver = NftablesFirewallDriver()
            import os
            if not os.path.exists(config.PATH_NFT):
                logger.error("Required firewall tool nft not found at %s. Network authorization will fail.", config.PATH_NFT)
        else:
            self.driver = MockFirewallDriver()

    def authorize(self, ip: str):
        self.driver.authorize(ip)
        # Apply per-client bandwidth limit
        try:
            _bandwidth.add_client(ip)
        except Exception as exc:
            logger.warning("Bandwidth limit failed for %s: %s", ip, exc)

    def remove(self, ip: str):
        self.driver.remove(ip)
        # Remove per-client bandwidth shaping
        try:
            _bandwidth.remove_client(ip)
        except Exception as exc:
            logger.warning("Bandwidth remove failed for %s: %s", ip, exc)

    def flush(self):
        self.driver.flush()

    def rebuild(self):
        pass
