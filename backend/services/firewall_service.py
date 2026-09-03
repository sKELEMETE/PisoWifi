import subprocess
import logging
import json
import os
import config
from abc import ABC, abstractmethod
from services.bandwidth_service import BandwidthService

logger = logging.getLogger(__name__)

_bandwidth = BandwidthService()


class FirewallDriver(ABC):

    @abstractmethod
    def authorize(self, ip: str, mac: str | None = None) -> None:
        pass

    @abstractmethod
    def remove(self, ip: str, mac: str | None = None) -> None:
        pass

    @abstractmethod
    def flush(self) -> None:
        pass

    @abstractmethod
    def get_active_elements(self) -> set[tuple[str, str]]:
        pass

    @abstractmethod
    def apply_batch(self, add_pairs: list[tuple[str, str]], remove_pairs: list[tuple[str, str]]) -> bool:
        pass

    @abstractmethod
    def rebuild_active_ruleset(self, authorizations: list[tuple[str, str]] | None = None) -> bool:
        pass


class NftablesFirewallDriver(FirewallDriver):

    def _resolve_mac(self, ip: str, mac: str | None = None) -> str:
        if mac and mac != "00:00:00:00:00:00":
            return mac.lower()
        try:
            from services.network_service import NetworkService
            resolved = NetworkService().get_client_mac(ip)
            if resolved and resolved != "00:00:00:00:00:00":
                return resolved.lower()
        except Exception:
            pass
        return "00:00:00:00:00:00"

    def _run(self, command, input_text: str | None = None, timeout: int = 10) -> subprocess.CompletedProcess:
        result = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return result

    def authorize(self, ip: str, mac: str | None = None) -> None:
        mac_addr = self._resolve_mac(ip, mac)
        elem_str = f"{ip} . {mac_addr}"
        logger.info("========== AUTHORIZE (nftables) ==========")
        logger.info("Pair = %s", elem_str)

        batch = (
            f"add element inet {config.NFT_TABLE_NAME} {config.NFT_SET_NAME} {{ {elem_str} }}\n"
            f"add element ip nat {config.NFT_SET_NAME} {{ {elem_str} }}\n"
        )
        try:
            self._run([config.PATH_NFT, "-f", "-"], input_text=batch)
        except RuntimeError as exc:
            logger.error("Failed to authorize nftables element %s: %s", elem_str, exc)
            raise

    def remove(self, ip: str, mac: str | None = None) -> None:
        logger.info("Removing %s (nftables)", ip)
        targets = []
        if mac:
            targets.append((ip, mac.lower()))
        else:
            active = self.get_active_elements()
            targets = [pair for pair in active if pair[0] == ip]

        if not targets:
            targets = [(ip, self._resolve_mac(ip, mac))]

        commands = []
        for pair_ip, pair_mac in targets:
            elem = f"{pair_ip} . {pair_mac}"
            commands.append(f"delete element inet {config.NFT_TABLE_NAME} {config.NFT_SET_NAME} {{ {elem} }}")
            commands.append(f"delete element ip nat {config.NFT_SET_NAME} {{ {elem} }}")

        if commands:
            batch = "\n".join(commands) + "\n"
            try:
                self._run([config.PATH_NFT, "-f", "-"], input_text=batch)
            except RuntimeError as exc:
                logger.warning("Ignored error during nftables delete for %s: %s", ip, exc)

    def flush(self) -> None:
        logger.info("Flushing firewall (nftables)")
        batch = (
            f"flush set inet {config.NFT_TABLE_NAME} {config.NFT_SET_NAME}\n"
            f"flush set ip nat {config.NFT_SET_NAME}\n"
        )
        try:
            self._run([config.PATH_NFT, "-f", "-"], input_text=batch)
        except RuntimeError as exc:
            logger.error("Failed to flush nftables sets: %s", exc)
            raise

    def get_active_elements(self) -> set[tuple[str, str]]:
        elements: set[tuple[str, str]] = set()
        cmd = [config.PATH_NFT, "-j", "list", "set", "inet", config.NFT_TABLE_NAME, config.NFT_SET_NAME]
        try:
            res = self._run(cmd)
            data = json.loads(res.stdout)
            for item in data.get("nftables", []):
                set_obj = item.get("set", {})
                raw_elems = set_obj.get("elem", [])
                for elem in raw_elems:
                    if isinstance(elem, dict) and "concat" in elem:
                        concat = elem["concat"]
                        if len(concat) >= 2:
                            elements.add((str(concat[0]), str(concat[1]).lower()))
                    elif isinstance(elem, str):
                        elements.add((elem, ""))
        except Exception as exc:
            logger.debug("Could not query nftables active elements: %s", exc)
        return elements

    def apply_batch(self, add_pairs: list[tuple[str, str]], remove_pairs: list[tuple[str, str]]) -> bool:
        if not add_pairs and not remove_pairs:
            return True

        commands = []
        for ip, mac in add_pairs:
            mac_addr = (mac or "00:00:00:00:00:00").lower()
            elem = f"{ip} . {mac_addr}"
            commands.append(f"add element inet {config.NFT_TABLE_NAME} {config.NFT_SET_NAME} {{ {elem} }}")
            commands.append(f"add element ip nat {config.NFT_SET_NAME} {{ {elem} }}")

        for ip, mac in remove_pairs:
            mac_addr = (mac or "00:00:00:00:00:00").lower()
            elem = f"{ip} . {mac_addr}"
            commands.append(f"delete element inet {config.NFT_TABLE_NAME} {config.NFT_SET_NAME} {{ {elem} }}")
            commands.append(f"delete element ip nat {config.NFT_SET_NAME} {{ {elem} }}")

        batch = "\n".join(commands) + "\n"
        try:
            self._run([config.PATH_NFT, "-f", "-"], input_text=batch)
            return True
        except RuntimeError as exc:
            logger.error("Failed executing nftables batch transaction: %s", exc)
            return False

    def rebuild_active_ruleset(self, authorizations: list[tuple[str, str]] | None = None) -> bool:
        template_path = os.path.join(config.BASE_DIR, "config/nftables/nftables.conf.template")
        if not os.path.exists(template_path):
            logger.error("nftables template missing at %s", template_path)
            return False

        with open(template_path, "r") as f:
            content = f.read()

        elements_decl = ""
        if authorizations:
            pairs_str = ", ".join(f"{ip} . {mac.lower()}" for ip, mac in authorizations)
            elements_decl = f"\n        elements = {{ {pairs_str} }}"

        rendered = content.format(
            nft_table_name=config.NFT_TABLE_NAME,
            nft_set_name=config.NFT_SET_NAME,
            lan_interface=config.LAN_INTERFACE,
            wan_interface=config.WAN_INTERFACE,
        )

        if elements_decl:
            rendered = rendered.replace(
                f"set {config.NFT_SET_NAME} {{\n        type ipv4_addr . ether_addr\n        flags timeout\n    }}",
                f"set {config.NFT_SET_NAME} {{\n        type ipv4_addr . ether_addr\n        flags timeout{elements_decl}\n    }}"
            )

        # Validate syntax first
        try:
            self._run([config.PATH_NFT, "-c", "-f", "-"], input_text=rendered)
        except RuntimeError as exc:
            logger.error("nftables rebuild validation failed: %s", exc)
            return False

        # Apply atomically
        try:
            self._run([config.PATH_NFT, "-f", "-"], input_text=rendered)
            logger.info("nftables active ruleset rebuilt successfully.")
            return True
        except RuntimeError as exc:
            logger.critical("Failed to apply rebuilt nftables ruleset: %s", exc)
            return False


class MockFirewallDriver(FirewallDriver):

    def __init__(self):
        self.active_pairs: set[tuple[str, str]] = set()

    @property
    def active_ips(self) -> set[str]:
        return {ip for ip, _ in self.active_pairs}

    @active_ips.setter
    def active_ips(self, val: set[str]):
        self.active_pairs = {(ip, "00:00:00:00:00:00") for ip in val}

    def authorize(self, ip: str, mac: str | None = None) -> None:
        mac_addr = (mac or "00:00:00:00:00:00").lower()
        logger.info("========== AUTHORIZE (mock) ==========")
        logger.info("IP = %s, MAC = %s added to allowed set", ip, mac_addr)
        self.active_pairs.add((ip, mac_addr))

    def remove(self, ip: str, mac: str | None = None) -> None:
        logger.info("Removing %s (mock)", ip)
        if mac:
            self.active_pairs.discard((ip, mac.lower()))
        else:
            self.active_pairs = {(i, m) for i, m in self.active_pairs if i != ip}

    def flush(self) -> None:
        logger.info("Flushing firewall (mock)")
        self.active_pairs.clear()

    def get_active_elements(self) -> set[tuple[str, str]]:
        return set(self.active_pairs)

    def apply_batch(self, add_pairs: list[tuple[str, str]], remove_pairs: list[tuple[str, str]]) -> bool:
        for ip, mac in add_pairs:
            self.active_pairs.add((ip, (mac or "00:00:00:00:00:00").lower()))
        for ip, mac in remove_pairs:
            mac_addr = (mac or "00:00:00:00:00:00").lower()
            self.active_pairs.discard((ip, mac_addr))
            if not mac:
                self.active_pairs = {(i, m) for i, m in self.active_pairs if i != ip}
        return True

    def rebuild_active_ruleset(self, authorizations: list[tuple[str, str]] | None = None) -> bool:
        if authorizations is not None:
            self.active_pairs = {(ip, (mac or "00:00:00:00:00:00").lower()) for ip, mac in authorizations}
        return True


class FirewallService:

    def __init__(self):
        driver_name = config.FIREWALL_DRIVER.lower()
        if driver_name == "nftables":
            self.driver: FirewallDriver = NftablesFirewallDriver()
            if not os.path.exists(config.PATH_NFT):
                logger.error("Required firewall tool nft not found at %s. Network authorization will fail.", config.PATH_NFT)
        else:
            self.driver: FirewallDriver = MockFirewallDriver()

    def authorize(self, ip: str, mac: str | None = None):
        self.driver.authorize(ip, mac=mac)
        try:
            _bandwidth.add_client(ip)
        except Exception as exc:
            logger.warning("Bandwidth limit failed for %s: %s", ip, exc)

    def remove(self, ip: str, mac: str | None = None):
        self.driver.remove(ip, mac=mac)
        try:
            _bandwidth.remove_client(ip)
        except Exception as exc:
            logger.warning("Bandwidth remove failed for %s: %s", ip, exc)

    def flush(self):
        self.driver.flush()

    def get_active_kernel_elements(self) -> set[tuple[str, str]]:
        return self.driver.get_active_elements()

    def apply_batch(self, add_pairs: list[tuple[str, str]], remove_pairs: list[tuple[str, str]]) -> bool:
        success = self.driver.apply_batch(add_pairs, remove_pairs)
        for ip, _ in add_pairs:
            try:
                _bandwidth.add_client(ip)
            except Exception:
                pass
        for ip, _ in remove_pairs:
            try:
                _bandwidth.remove_client(ip)
            except Exception:
                pass
        return success

    def rebuild_active_ruleset(self, authorizations: list[tuple[str, str]] | None = None) -> bool:
        return self.driver.rebuild_active_ruleset(authorizations)

    def rebuild(self):
        return self.rebuild_active_ruleset()
