# System Architecture

## 1. Hardware
- **Core Server**: Ubuntu Server PC/SBC handling processing, networking, routing, and database.
- **Coin Acceptor**: Hardware device that validates physical coins.
- **Arduino Interface**: Translates electronic pulses from the coin acceptor into Serial data strings over USB/TTY.
- **Network AP Router**: Broadcasts the WiFi signal. Configured as a dumb AP or bridged mode so the Ubuntu Server handles DHCP/DNS.

## 2. Networking layer
- **DHCP/DNS**: Typically `dnsmasq` or `systemd-networkd` assigns IP addresses to connected clients and resolves captive portal redirects.
- **Firewall (`nftables`)**:
  - Redirects port 80 traffic from unauthenticated users to the Nginx captive portal.
  - Allows internet access for MAC addresses with an `ACTIVE` session status.
- **Bandwidth Shaping (`tc`)**:
  - Egress (Download): Handled via HTB qdisc on the physical network interface (e.g., `enxc817f552a5c6`).
  - Ingress (Upload): Traffic is redirected via `act_mirred` to an Intermediate Functional Block device (`ifb0`), where another HTB qdisc shapes it.

## 3. Backend (FastAPI)
- Uses a Service-Repository pattern.
- **Services**: 
  - `FirewallService`: Maps Python calls to shell `nftables` commands.
  - `BandwidthService`: Maps Python calls to shell `tc` commands.
  - `CoinService`: Reads `/dev/ttyUSBx`, maintains internal reservation lock logic.
  - `SessionService`: Manages business logic of time left, state transitions.
- **Schedulers**: Background tasks checking for expired sessions and updating state.

## 4. Frontend (React)
- SPA (Single Page Application) built with Vite.
- Manages routing based on Session State (`UNKNOWN`, `ACTIVE`, `PAUSED`).
- Implements `SoundManager` for audio feedback triggered by coin insertion states.
- Handled by Nginx which provides the Captive Portal payload (handling Apple, Android, Windows captive portal probe URLs).
