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


class NetworkService:

    def __init__(self):
        provider_name = config.NETWORK_PROVIDER.lower()
        if provider_name == "local_arp":
            self.provider = LocalArpNetworkProvider()
        else:
            self.provider = MockNetworkProvider()

    def get_client_ip(self, request):
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "127.0.0.1"

    def get_client_mac(self, ip_address):
        return self.provider.get_client_mac(ip_address)

    def get_hostname(self, ip_address):
        try:
            return socket.gethostbyaddr(ip_address)[0]
        except socket.herror:
            return "Unknown"
