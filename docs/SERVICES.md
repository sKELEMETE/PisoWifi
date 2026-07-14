# Backend Services Documentation

## 1. `BandwidthService`
- **Purpose**: Applies per-user speed limits.
- **Dependencies**: Linux `tc` (Traffic Control), `iproute2`, kernel module `ifb`.
- **Methods**:
  - `setup()`: Initializes root HTB qdiscs and `ifb0` on startup. Idempotent.
  - `apply_limit(ip, mac)`: Creates class and `u32` filters for 10Mbps up/down.
  - `remove_limit(ip, mac)`: Deletes the specific `u32` filters using strict `prio 1` matching.

## 2. `FirewallService`
- **Purpose**: Grants or revokes internet access.
- **Dependencies**: Linux `nftables`.
- **Methods**:
  - `allow_mac(mac)`: Adds MAC to the authorized NFT set.
  - `block_mac(mac)`: Removes MAC from the authorized NFT set.

## 3. `CoinService`
- **Purpose**: Interacts with the Arduino hardware via Serial and manages locking.
- **Dependencies**: `pyserial`.
- **Logic**:
  - Holds a `current_owner_mac` variable.
  - If a user triggers "Insert Coin", sets `current_owner_mac` and enables the Arduino acceptor.
  - Listeners read pulses (1 pulse = 1 peso).
  - Emits real-time data back to the requester.
  - Releases lock on timeout (30s) or "Done" click.

## 4. `SessionService`
- **Purpose**: Core business logic for session lifecycle.
- **Dependencies**: Database, `FirewallService`, `BandwidthService`.
- **Logic**:
  - `pause_session(mac)`: Calculates elapsed time, stops countdown, calls Firewall and Bandwidth services to revoke access.
  - `resume_session(mac)`: Restarts countdown, calls Firewall and Bandwidth services to restore access.

## 5. `SchedulerService`
- **Purpose**: Background tasks.
- **Logic**: Periodically checks for expired sessions (remaining_seconds <= 0). Calls `SessionService` to terminate them and clean up firewall/bandwidth rules.
