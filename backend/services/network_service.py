import socket
import logging
import config
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NetworkProvider(ABC):

    @abstractmethod
    def get_client_mac(self, ip_address: str) -> str:
        pass


class LocalArpNetworkProvider(NetworkProvider):

    def get_client_mac(self, ip_address: str) -> str:
        try:
            with open("/proc/net/arp", "r") as arp_table:
                for line in arp_table:
                    parts = line.split()
                    if len(parts) >= 4 and parts[0] == ip_address:
                        return parts[3].upper()
        except FileNotFoundError:
            pass
        return "00:00:00:00:00:00"


class MockNetworkProvider(NetworkProvider):

    def get_client_mac(self, ip_address: str) -> str:
        # Generate a deterministic mock MAC based on IP hash for local testing
        if ip_address == "127.0.0.1":
            return "00:00:00:00:00:01"
        last_octet = ip_address.rsplit(".", 1)[-1]
        try:
            hex_val = f"{int(last_octet):02X}"
        except ValueError:
            hex_val = "FF"
        return f"00:11:22:33:44:{hex_val}"


import ipaddress

TRUSTED_PROXIES = {"127.0.0.1", "::1"}


class NetworkService:

    def __init__(self):
        provider_name = config.NETWORK_PROVIDER.lower()
        if provider_name == "local_arp":
            self.provider = LocalArpNetworkProvider()
        else:
            self.provider = MockNetworkProvider()

    def get_client_ip(self, request) -> str:
        direct_ip = request.client.host if request.client else "127.0.0.1"
        try:
            ipaddress.ip_address(direct_ip)
        except ValueError:
            direct_ip = "127.0.0.1"

        # Only trust proxy headers when direct connection originates from a trusted local reverse proxy (Nginx)
        if direct_ip in TRUSTED_PROXIES:
            is_dev = config.DEBUG or config.ENVIRONMENT in ("development", "dev", "test")
            if is_dev:
                test_ip = request.headers.get("X-Test-Client-IP")
                if test_ip:
                    try:
                        ipaddress.ip_address(test_ip.strip())
                        return test_ip.strip()
                    except ValueError:
                        pass

            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                candidate = real_ip.strip()
                try:
                    ipaddress.ip_address(candidate)
                    return candidate
                except ValueError:
                    pass

            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                candidate = forwarded.split(",")[0].strip()
                try:
                    ipaddress.ip_address(candidate)
                    return candidate
                except ValueError:
                    pass

        return direct_ip

    def get_client_mac(self, ip_address: str, request=None) -> str:
        is_dev = config.DEBUG or config.ENVIRONMENT in ("development", "dev", "test")
        if is_dev and request is not None:
            test_mac = request.headers.get("X-Test-Client-MAC")
            if test_mac:
                return test_mac.strip().upper()

        return self.provider.get_client_mac(ip_address)

    def get_hostname(self, ip_address: str) -> str:
        try:
            return socket.gethostbyaddr(ip_address)[0]
        except socket.herror:
            return "Unknown"
