# Network Documentation

## 1. Interface Layout
- **Physical Interface (e.g., `eth1` or `enxc8...`)**: The interface facing the WiFi Access Point.
- **Intermediate Functional Block (`ifb0`)**: A virtual kernel interface used to shape incoming (upload) traffic, since standard `tc` shaping natively only applies to egress (download) traffic.

## 2. DHCP & DNS
The Ubuntu server provides IPs and DNS via standard Linux tooling (`dnsmasq` or similar). All DNS requests from unauthenticated clients are spoofed to point to the server's IP address (10.0.0.1) for captive portal redirection.

## 3. Captive Portal (Nginx & nftables)
- `nftables` forces HTTP (Port 80) traffic to Nginx if the MAC address is NOT in the authorized list.
- Nginx intercepts specific URLs (e.g. `/generate_204` for Android, `/hotspot-detect.html` for Apple) and replies with a `302 Redirect` to `http://10.0.0.1/` to trigger the captive portal prompt.

## 4. Internet Authorization Flow
1. Device connects, receives IP.
2. Captive Portal pops up.
3. User pays for time.
4. Backend `FirewallService` adds MAC to `nftables` authorized set.
5. Backend `BandwidthService` adds `tc` rules.
6. Internet access is immediately available.

## 5. Traffic Control (`tc`) Bandwidth Shaping
To ensure fair usage, every authenticated user gets a dedicated 10 Mbps Up / 10 Mbps Down limit.
- **Egress (Download)**: HTB qdisc applied directly to the physical interface. Traffic is matched by destination IP/MAC and sent to a 10mbit class.
- **Ingress (Upload)**: An `ingress` qdisc on the physical interface mirrors traffic to `ifb0` using `act_mirred`. `ifb0` runs an HTB qdisc. Traffic is matched by source IP/MAC and shaped to 10mbit.
- **Important Rule**: `prio 1` is strictly used when adding `u32` filters so they can be reliably deleted using the exact same priority upon session Pause or Expiration.
