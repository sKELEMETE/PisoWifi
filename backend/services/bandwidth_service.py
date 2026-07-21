import ipaddress
import logging
import subprocess
import config
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

IFB_IFACE = "ifb0"
RATE = config.BANDWIDTH_RATE
CEIL = config.BANDWIDTH_CEIL
DEFAULT_CLASS = "9999"


# ─────────────────────────────────────────────────────────────
# Interface auto-detection
# ─────────────────────────────────────────────────────────────

def _detect_lan_iface() -> str:
    """
    Return the network interface that serves the LAN (client-facing) subnet.

    Strategy:
      1. Read /proc/net/route to find all non-default routes.
      2. Select the interface that has a route to a RFC-1918 private range
         that is NOT the default gateway interface.
      3. Fallback: return config.LAN_INTERFACE_FALLBACK.
    """
    default_iface = None
    candidates: list[tuple[str, int]] = []   # (iface, prefix_len)

    try:
        with open("/proc/net/route") as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if len(parts) < 8:
                    continue
                iface = parts[0]
                dest_hex = parts[1]
                mask_hex = parts[7]
                flags = int(parts[3], 16)

                dest = int(dest_hex, 16)
                mask = int(mask_hex, 16)

                # Flag 0x0001 = RTF_UP, 0x0002 = RTF_GATEWAY
                if dest == 0 and (flags & 0x0002):
                    default_iface = iface
                    continue

                if dest == 0:
                    continue

                # Convert little-endian hex to IP
                dest_ip = ipaddress.IPv4Address(dest.to_bytes(4, "little"))
                mask_int = int.from_bytes(mask.to_bytes(4, "little"), "big")
                prefix_len = bin(mask_int).count("1")

                # Only consider RFC-1918 ranges
                if dest_ip.is_private:
                    candidates.append((iface, prefix_len))
    except Exception as exc:
        logger.warning("LAN iface detection failed: %s", exc)

    # Prefer the most specific (longest prefix) private-network route
    # that isn't the WAN default gateway interface
    for iface, _ in sorted(candidates, key=lambda x: -x[1]):
        if iface != default_iface:
            return iface

    # Fallback
    return config.LAN_INTERFACE_FALLBACK


# Module-level: detect once at import time
_LAN_IFACE: str = _detect_lan_iface()
logger.info("BandwidthService LAN interface: %s", _LAN_IFACE)


class BandwidthDriver(ABC):

    @abstractmethod
    def setup(self) -> None:
        pass

    @abstractmethod
    def add_client(self, ip: str) -> None:
        pass

    @abstractmethod
    def remove_client(self, ip: str) -> None:
        pass


class LinuxTcBandwidthDriver(BandwidthDriver):

    def _run(self, cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
        # Use absolute paths for system tools to avoid path resolution issues in systemd environment
        abs_cmd = list(cmd)
        if abs_cmd:
            if abs_cmd[0] == "tc":
                abs_cmd[0] = config.PATH_TC
            elif abs_cmd[0] == "ip":
                abs_cmd[0] = config.PATH_IP
            elif abs_cmd[0] == "modprobe":
                abs_cmd[0] = config.PATH_MODPROBE
        result = subprocess.run(abs_cmd, capture_output=True, text=True, timeout=10)
        if check and result.returncode != 0:
            raise RuntimeError(f"tc error ({' '.join(abs_cmd)}): {result.stderr.strip()}")
        return result

    def _ip_to_class_id(self, ip: str) -> int:
        try:
            last = int(ip.rsplit(".", 1)[-1])
            if last == 0:
                return 1
            if last == int(DEFAULT_CLASS):
                return 1
            return last
        except (ValueError, IndexError):
            cid = (hash(ip) % 65533) + 1
            return cid if cid != int(DEFAULT_CLASS) else 1

    def setup(self) -> None:
        import os
        for name, path in [("tc", config.PATH_TC), ("ip", config.PATH_IP), ("modprobe", config.PATH_MODPROBE)]:
            if not os.path.exists(path):
                logger.error("Required tool %s not found at %s. Bandwidth shaping setup may fail.", name, path)
        self._setup_ifb()
        self._setup_egress_root()
        self._setup_ingress_root()
        logger.info("LinuxTcBandwidthDriver setup complete on %s + %s.", _LAN_IFACE, IFB_IFACE)

    def add_client(self, ip: str) -> None:
        cid = self._ip_to_class_id(ip)
        self._add_egress_class(ip, cid)
        self._add_ingress_class(ip, cid)
        logger.info("Bandwidth limit applied (tc) for %s → class %d.", ip, cid)

    def remove_client(self, ip: str) -> None:
        cid = self._ip_to_class_id(ip)
        self._del_egress_class(ip, cid)
        self._del_ingress_class(ip, cid)
        logger.info("Bandwidth limit removed (tc) for %s.", ip)

    def _setup_ifb(self):
        self._run(["modprobe", "ifb", "numifbs=1"], check=False)
        self._run(["ip", "link", "set", IFB_IFACE, "up"], check=False)

    def _setup_egress_root(self):
        existing = self._run(["tc", "qdisc", "show", "dev", _LAN_IFACE, "root"], check=False)
        if "htb" in existing.stdout:
            logger.debug("Egress HTB qdisc already exists on %s — skipping.", _LAN_IFACE)
            return
        self._run(["tc", "qdisc", "del", "dev", _LAN_IFACE, "root"], check=False)
        self._run([
            "tc", "qdisc", "add", "dev", _LAN_IFACE,
            "root", "handle", "1:", "htb", "default", DEFAULT_CLASS,
        ])
        self._run([
            "tc", "class", "add", "dev", _LAN_IFACE,
            "parent", "1:", "classid", f"1:{DEFAULT_CLASS}",
            "htb", "rate", "1000mbit",
        ])

    def _setup_ingress_root(self):
        existing = self._run(
            ["tc", "qdisc", "show", "dev", _LAN_IFACE, "ingress"], check=False
        )
        if "ingress" not in existing.stdout:
            self._run([
                "tc", "qdisc", "add", "dev", _LAN_IFACE,
                "handle", "ffff:", "ingress",
            ])
            self._run([
                "tc", "filter", "add", "dev", _LAN_IFACE,
                "parent", "ffff:", "matchall",
                "action", "mirred", "egress", "redirect", "dev", IFB_IFACE,
            ])
        else:
            logger.debug("Ingress qdisc already exists on %s — skipping.", _LAN_IFACE)

        existing_ifb = self._run(
            ["tc", "qdisc", "show", "dev", IFB_IFACE, "root"], check=False
        )
        if "htb" in existing_ifb.stdout:
            logger.debug("Ingress HTB qdisc already exists on %s — skipping.", IFB_IFACE)
            return
        self._run(["tc", "qdisc", "del", "dev", IFB_IFACE, "root"], check=False)
        self._run([
            "tc", "qdisc", "add", "dev", IFB_IFACE,
            "root", "handle", "2:", "htb", "default", DEFAULT_CLASS,
        ])
        self._run([
            "tc", "class", "add", "dev", IFB_IFACE,
            "parent", "2:", "classid", f"2:{DEFAULT_CLASS}",
            "htb", "rate", "1000mbit",
        ])

    def _add_egress_class(self, ip: str, cid: int):
        self._run([
            "tc", "class", "add", "dev", _LAN_IFACE,
            "parent", "1:", "classid", f"1:{cid}",
            "htb", "rate", RATE, "ceil", CEIL,
        ], check=False)
        self._run([
            "tc", "filter", "add", "dev", _LAN_IFACE,
            "parent", "1:", "protocol", "ip", "prio", "1",
            "handle", f"800::{cid:x}",
            "u32", "match", "ip", "dst", f"{ip}/32",
            "flowid", f"1:{cid}",
        ], check=False)

    def _del_egress_class(self, ip: str, cid: int):
        self._run([
            "tc", "filter", "del", "dev", _LAN_IFACE,
            "parent", "1:", "protocol", "ip", "prio", "1",
            "handle", f"800::{cid:x}",
            "u32",
        ], check=False)
        self._run([
            "tc", "class", "del", "dev", _LAN_IFACE,
            "classid", f"1:{cid}",
        ], check=False)

    def _add_ingress_class(self, ip: str, cid: int):
        self._run([
            "tc", "class", "add", "dev", IFB_IFACE,
            "parent", "2:", "classid", f"2:{cid}",
            "htb", "rate", RATE, "ceil", CEIL,
        ], check=False)
        self._run([
            "tc", "filter", "add", "dev", IFB_IFACE,
            "parent", "2:", "protocol", "ip", "prio", "1",
            "handle", f"800::{cid:x}",
            "u32", "match", "ip", "src", f"{ip}/32",
            "flowid", f"2:{cid}",
        ], check=False)

    def _del_ingress_class(self, ip: str, cid: int):
        self._run([
            "tc", "filter", "del", "dev", IFB_IFACE,
            "parent", "2:", "protocol", "ip", "prio", "1",
            "handle", f"800::{cid:x}",
            "u32",
        ], check=False)
        self._run([
            "tc", "class", "del", "dev", IFB_IFACE,
            "classid", f"2:{cid}",
        ], check=False)


class MockBandwidthDriver(BandwidthDriver):

    def setup(self) -> None:
        logger.info("MockBandwidthDriver setup completed successfully.")

    def add_client(self, ip: str) -> None:
        logger.info("MockBandwidthDriver: added client %s at rate %s", ip, RATE)

    def remove_client(self, ip: str) -> None:
        logger.info("MockBandwidthDriver: removed client %s", ip)


class BandwidthService:

    def __init__(self):
        driver_name = config.BANDWIDTH_DRIVER.lower()
        if driver_name == "linux_tc":
            self.driver = LinuxTcBandwidthDriver()
        else:
            self.driver = MockBandwidthDriver()

    def setup(self):
        self.driver.setup()

    def add_client(self, ip: str):
        self.driver.add_client(ip)

    def remove_client(self, ip: str):
        self.driver.remove_client(ip)
