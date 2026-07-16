"""
BandwidthService – per-client 10 Mbps up/down shaping via Linux TC + HTB + IFB.

Packet classification:
──────────────────────────────────────────────────────────────────────────────
DOWNLOAD (server → client):
  - Packets leave the LAN interface as egress traffic.
  - Root qdisc on LAN iface: HTB handle 1:, default class 1:9999 (unthrottled).
  - Per-client HTB class 1:<cid> at rate/ceil 10mbit.
  - tc filter (u32): match ip dst <client_ip>/32 → flowid 1:<cid>
  - Result: every IP packet destined for client_ip is enqueued into the
    10 Mbit HTB class, capping download to 10 Mbit/s.

UPLOAD (client → server):
  - Linux tc cannot shape ingress traffic directly; the IFB trick is used.
  - An ingress qdisc (ffff:) is attached to the LAN interface.
  - A matchall filter redirects ALL ingress frames to ifb0 via mirred action.
  - ifb0 receives the redirected frames as its own egress traffic.
  - Root qdisc on ifb0: HTB handle 2:, default class 2:9999 (unthrottled).
  - Per-client HTB class 2:<cid> at rate/ceil 10mbit.
  - tc filter (u32): match ip src <client_ip>/32 → flowid 2:<cid>
  - Result: every IP packet sourced from client_ip is shaped to 10 Mbit/s.

Class ID derivation:
  - Last octet of IP address (for /24 subnets this is always unique).
  - e.g. 10.0.0.120 → cid 120, 10.0.0.5 → cid 5.
  - Special value 9999 reserved for the default (unthrottled) class.
──────────────────────────────────────────────────────────────────────────────
"""

import ipaddress
import logging
import subprocess

logger = logging.getLogger(__name__)

IFB_IFACE = "ifb0"
RATE = "10mbit"
CEIL = "10mbit"
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
      3. Fallback: return 'enxc817f552a5c6' (the known LAN iface on this box).
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
    return "enxc817f552a5c6"


# Module-level: detect once at import time
_LAN_IFACE: str = _detect_lan_iface()
logger.info("BandwidthService LAN interface: %s", _LAN_IFACE)


# ─────────────────────────────────────────────────────────────
# tc helper
# ─────────────────────────────────────────────────────────────

def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    # Use absolute paths for system tools to avoid path resolution issues in systemd environment
    abs_cmd = list(cmd)
    if abs_cmd:
        if abs_cmd[0] == "tc":
            abs_cmd[0] = "/usr/sbin/tc"
        elif abs_cmd[0] == "ip":
            abs_cmd[0] = "/usr/sbin/ip"
        elif abs_cmd[0] == "modprobe":
            abs_cmd[0] = "/usr/sbin/modprobe"
    result = subprocess.run(abs_cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"tc error ({' '.join(abs_cmd)}): {result.stderr.strip()}")
    return result


def _ip_to_class_id(ip: str) -> int:
    """
    Derive a unique tc class ID from the client IP.

    For a /24 subnet the last octet is always unique.
    Reserves 9999 for the default unthrottled class.
    """
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


# ─────────────────────────────────────────────────────────────
# BandwidthService
# ─────────────────────────────────────────────────────────────

class BandwidthService:
    """Manages per-client 10 Mbps HTB shaping on the LAN interface."""

    def setup(self):
        """
        Idempotent one-time setup.  Safe to call on every backend restart.
        Creates root qdiscs and IFB redirect only if they are not already present.
        """
        self._setup_ifb()
        self._setup_egress_root()
        self._setup_ingress_root()
        logger.info("BandwidthService setup complete on %s + %s.", _LAN_IFACE, IFB_IFACE)

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def add_client(self, ip: str):
        """Apply 10 Mbit/s download + upload limit for client IP."""
        cid = _ip_to_class_id(ip)
        self._add_egress_class(ip, cid)
        self._add_ingress_class(ip, cid)
        logger.info("Bandwidth limit applied for %s → class %d.", ip, cid)

    def remove_client(self, ip: str):
        """Remove all bandwidth shaping for client IP."""
        cid = _ip_to_class_id(ip)
        self._del_egress_class(ip, cid)
        self._del_ingress_class(ip, cid)
        logger.info("Bandwidth limit removed for %s.", ip)

    # ──────────────────────────────────────────
    # Root qdisc / IFB setup
    # ──────────────────────────────────────────

    def _setup_ifb(self):
        """Load ifb kernel module and bring ifb0 up."""
        _run(["modprobe", "ifb", "numifbs=1"], check=False)
        _run(["ip", "link", "set", IFB_IFACE, "up"], check=False)

    def _setup_egress_root(self):
        """
        Create HTB root qdisc on LAN egress (download).
        Skip if HTB is already present (idempotent).
        """
        existing = _run(["tc", "qdisc", "show", "dev", _LAN_IFACE, "root"], check=False)
        if "htb" in existing.stdout:
            logger.debug("Egress HTB qdisc already exists on %s — skipping.", _LAN_IFACE)
            return
        # Remove whatever qdisc is there (e.g. fq_codel default)
        _run(["tc", "qdisc", "del", "dev", _LAN_IFACE, "root"], check=False)
        _run([
            "tc", "qdisc", "add", "dev", _LAN_IFACE,
            "root", "handle", "1:", "htb", "default", DEFAULT_CLASS,
        ])
        # Default class — unthrottled, for portal traffic and non-authenticated clients
        _run([
            "tc", "class", "add", "dev", _LAN_IFACE,
            "parent", "1:", "classid", f"1:{DEFAULT_CLASS}",
            "htb", "rate", "1000mbit",
        ])

    def _setup_ingress_root(self):
        """
        Attach ingress qdisc to LAN iface and redirect all ingress to ifb0.
        Then create HTB root on ifb0 (upload shaping).
        """
        # 1. Ingress qdisc on LAN iface
        existing = _run(
            ["tc", "qdisc", "show", "dev", _LAN_IFACE, "ingress"], check=False
        )
        if "ingress" not in existing.stdout:
            _run([
                "tc", "qdisc", "add", "dev", _LAN_IFACE,
                "handle", "ffff:", "ingress",
            ])
            # Redirect ALL ingress packets → ifb0 egress via mirred
            _run([
                "tc", "filter", "add", "dev", _LAN_IFACE,
                "parent", "ffff:", "matchall",
                "action", "mirred", "egress", "redirect", "dev", IFB_IFACE,
            ])
        else:
            logger.debug("Ingress qdisc already exists on %s — skipping.", _LAN_IFACE)

        # 2. HTB root on ifb0
        existing_ifb = _run(
            ["tc", "qdisc", "show", "dev", IFB_IFACE, "root"], check=False
        )
        if "htb" in existing_ifb.stdout:
            logger.debug("Ingress HTB qdisc already exists on %s — skipping.", IFB_IFACE)
            return
        _run(["tc", "qdisc", "del", "dev", IFB_IFACE, "root"], check=False)
        _run([
            "tc", "qdisc", "add", "dev", IFB_IFACE,
            "root", "handle", "2:", "htb", "default", DEFAULT_CLASS,
        ])
        _run([
            "tc", "class", "add", "dev", IFB_IFACE,
            "parent", "2:", "classid", f"2:{DEFAULT_CLASS}",
            "htb", "rate", "1000mbit",
        ])

    # ──────────────────────────────────────────
    # Per-client egress (download) class + filter
    # ──────────────────────────────────────────

    def _add_egress_class(self, ip: str, cid: int):
        # HTB class — caps download at 10 Mbit/s
        _run([
            "tc", "class", "add", "dev", _LAN_IFACE,
            "parent", "1:", "classid", f"1:{cid}",
            "htb", "rate", RATE, "ceil", CEIL,
        ], check=False)  # ignore "already exists" errors
        # u32 filter — matches packets whose IPv4 destination = client_ip
        _run([
            "tc", "filter", "add", "dev", _LAN_IFACE,
            "parent", "1:", "protocol", "ip", "prio", "1",
            "handle", f"800::{cid:x}",
            "u32", "match", "ip", "dst", f"{ip}/32",
            "flowid", f"1:{cid}",
        ], check=False)

    def _del_egress_class(self, ip: str, cid: int):
        # Delete filter first (required before class deletion on many kernels)
        _run([
            "tc", "filter", "del", "dev", _LAN_IFACE,
            "parent", "1:", "protocol", "ip", "prio", "1",
            "handle", f"800::{cid:x}",
            "u32",
        ], check=False)
        _run([
            "tc", "class", "del", "dev", _LAN_IFACE,
            "classid", f"1:{cid}",
        ], check=False)

    # ──────────────────────────────────────────
    # Per-client ingress (upload) class + filter on ifb0
    # ──────────────────────────────────────────

    def _add_ingress_class(self, ip: str, cid: int):
        # HTB class — caps upload at 10 Mbit/s
        _run([
            "tc", "class", "add", "dev", IFB_IFACE,
            "parent", "2:", "classid", f"2:{cid}",
            "htb", "rate", RATE, "ceil", CEIL,
        ], check=False)
        # u32 filter — matches packets whose IPv4 source = client_ip
        # (these are client uploads, appearing as ifb0 egress after redirect)
        _run([
            "tc", "filter", "add", "dev", IFB_IFACE,
            "parent", "2:", "protocol", "ip", "prio", "1",
            "handle", f"800::{cid:x}",
            "u32", "match", "ip", "src", f"{ip}/32",
            "flowid", f"2:{cid}",
        ], check=False)

    def _del_ingress_class(self, ip: str, cid: int):
        _run([
            "tc", "filter", "del", "dev", IFB_IFACE,
            "parent", "2:", "protocol", "ip", "prio", "1",
            "handle", f"800::{cid:x}",
            "u32",
        ], check=False)
        _run([
            "tc", "class", "del", "dev", IFB_IFACE,
            "classid", f"2:{cid}",
        ], check=False)
