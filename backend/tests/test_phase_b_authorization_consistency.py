import os
import uuid
import pytest
from datetime import datetime, timedelta
from database import SessionLocal
from models.client import Client, ClientStatus
from models.session import Session as SessionModel, SessionStatus, ClientLiveSession
from models.rate import Rate
from models.network_authorization import NetworkAuthorization, NetworkAuthState
from services.firewall_service import FirewallService, MockFirewallDriver
from services.firewall_reconciler import FirewallReconciler
from services.session_service import SessionService
from repositories.session_repository import SessionRepository
from utils.time_utils import get_utc_now


def gen_mac():
    raw = uuid.uuid4().hex[:12].upper()
    return ":".join(raw[i:i+2] for i in range(0, 12, 2))


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_transactional_network_authorization_state_transitions(db):
    """
    Verify that session lifecycle transitions (create, pause, resume)
    durably update the NetworkAuthorization transactional outbox table.
    """
    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="192.168.4.101", status=ClientStatus.ONLINE)
    db.add(client)
    db.commit()

    rate = db.query(Rate).first()
    if not rate:
        rate = Rate(coin_value=5, minutes=60, enabled=True)
        db.add(rate)
        db.commit()

    mock_driver = MockFirewallDriver()
    firewall = FirewallService()
    firewall.driver = mock_driver

    sess_service = SessionService(SessionRepository(db), firewall_service=firewall)

    # 1. Create session -> Desired state must be AUTHORIZED
    session = sess_service.create_or_extend_session(client.id, rate.id, 60, authorize=True)
    auth = db.query(NetworkAuthorization).filter(NetworkAuthorization.client_id == client.id).first()
    assert auth is not None
    assert auth.desired_state == NetworkAuthState.AUTHORIZED.value
    assert auth.applied_state == NetworkAuthState.AUTHORIZED.value
    assert (client.current_ip, mac.lower()) in mock_driver.active_pairs

    # 2. Pause session -> Desired state must become BLOCKED
    sess_service.pause_session(client.id)
    db.refresh(auth)
    assert auth.desired_state == NetworkAuthState.BLOCKED.value
    assert auth.applied_state == NetworkAuthState.BLOCKED.value
    assert (client.current_ip, mac.lower()) not in mock_driver.active_pairs

    # 3. Resume session -> Desired state returns to AUTHORIZED
    sess_service.resume_session(client.id)
    db.refresh(auth)
    assert auth.desired_state == NetworkAuthState.AUTHORIZED.value
    assert auth.applied_state == NetworkAuthState.AUTHORIZED.value
    assert (client.current_ip, mac.lower()) in mock_driver.active_pairs


def test_firewall_reconciler_restores_dropped_authorization(db):
    """
    Verify continuous reconciler detects and restores authorization dropped from kernel set.
    """
    mac = gen_mac()
    client = Client(mac_address=mac, current_ip="192.168.4.102", status=ClientStatus.ONLINE)
    db.add(client)
    db.commit()

    now = get_utc_now()
    auth = NetworkAuthorization(
        client_id=client.id,
        mac_address=mac,
        ip_address=client.current_ip,
        desired_state=NetworkAuthState.AUTHORIZED.value,
        applied_state=NetworkAuthState.AUTHORIZED.value,
        created_at=now,
        updated_at=now,
    )
    db.add(auth)
    db.commit()

    mock_driver = MockFirewallDriver()
    # Kernel set is empty (simulating dropped state or firewall crash/restart)
    assert len(mock_driver.active_pairs) == 0

    firewall = FirewallService()
    firewall.driver = mock_driver

    reconciler = FirewallReconciler(firewall_service=firewall)
    metrics = reconciler.reconcile_once(db)

    assert metrics["false_deny_count"] >= 1
    # Pair should be restored to running firewall
    assert (client.current_ip, mac.lower()) in mock_driver.active_pairs
    db.refresh(auth)
    assert auth.applied_state == NetworkAuthState.AUTHORIZED.value


def test_firewall_reconciler_evicts_stale_orphan_authorization(db):
    """
    Verify continuous reconciler detects and removes unauthorized/stale kernel entries.
    """
    mock_driver = MockFirewallDriver()
    # Kernel has an unauthorized IP+MAC pair
    stale_ip = "192.168.4.199"
    stale_mac = "AA:BB:CC:DD:EE:FF".lower()
    mock_driver.active_pairs.add((stale_ip, stale_mac))

    firewall = FirewallService()
    firewall.driver = mock_driver

    reconciler = FirewallReconciler(firewall_service=firewall)
    metrics = reconciler.reconcile_once(db)

    assert metrics["stale_allow_count"] >= 1
    # Stale pair must be purged from active firewall
    assert (stale_ip, stale_mac) not in mock_driver.active_pairs


def test_anti_spoofing_hardened_binding_in_ruleset():
    """
    Verify the nftables template and concrete config enforce both ether saddr and ip saddr
    as well as interface boundaries.
    """
    import config
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    base = config.BASE_DIR if os.path.exists(os.path.join(config.BASE_DIR, "config/nftables/nftables.conf")) else repo_root

    conf_path = os.path.join(base, "config/nftables/nftables.conf")
    template_path = os.path.join(base, "config/nftables/nftables.conf.template")

    for path in (conf_path, template_path):
        with open(path, "r") as f:
            content = f.read()

        assert "type ipv4_addr . ether_addr" in content, f"Missing IP+MAC concatenation type in {path}"
        assert "ip saddr . ether saddr @" in content, f"Missing anti-spoofing rule in {path}"
        assert "policy drop" in content, f"Input or forward policy is not drop in {path}"


def test_nftables_syntax_validation_in_namespace():
    """
    Verify that generated nftables ruleset with IP+MAC pairs passes nft -c validation.
    """
    import subprocess
    import shutil
    nft_bin = shutil.which("nft") or "/usr/sbin/nft"
    unshare_bin = shutil.which("unshare")

    if not unshare_bin or not os.path.exists(nft_bin):
        pytest.skip("unshare or nft not available for isolated namespace validation")

    ruleset = """
    table inet pisowifi {
        set authenticated_clients {
            type ipv4_addr . ether_addr
            flags timeout
            elements = { 10.0.0.15 . aa:bb:cc:dd:ee:01 }
        }

        chain input {
            type filter hook input priority filter; policy drop;
            iifname "lo" accept
            ct state established,related accept
            iifname "wlan0" udp sport 68 udp dport 67 accept
            iifname "wlan0" udp dport 53 accept
            iifname "wlan0" tcp dport 53 accept
            iifname "wlan0" tcp dport 80 accept
            iifname "wlan0" tcp dport 443 accept
        }

        chain forward {
            type filter hook forward priority filter; policy drop;
            ct state established,related accept
            iifname "wlan0" oifname "eth0" ip saddr . ether saddr @authenticated_clients accept
        }

        chain output {
            type filter hook output priority filter; policy accept;
        }
    }
    """

    res = subprocess.run(
        [unshare_bin, "-U", "-r", "-n", nft_bin, "-c", "-f", "-"],
        input=ruleset,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert res.returncode == 0, f"nft validation failed: {res.stderr}"


def test_firewall_rebuild_active_ruleset():
    """
    Verify FirewallService.rebuild_active_ruleset executes correctly.
    """
    firewall = FirewallService()
    mock_driver = MockFirewallDriver()
    firewall.driver = mock_driver

    authorizations = [
        ("192.168.4.10", "AA:BB:CC:DD:EE:01"),
        ("192.168.4.11", "AA:BB:CC:DD:EE:02"),
    ]

    success = firewall.rebuild_active_ruleset(authorizations)
    assert success is True
    assert ("192.168.4.10", "aa:bb:cc:dd:ee:01") in mock_driver.active_pairs
    assert ("192.168.4.11", "aa:bb:cc:dd:ee:02") in mock_driver.active_pairs
