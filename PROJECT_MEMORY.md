# Project Memory

## Current Project Status
The project is fully functional with the captive portal, session lifecycle, coin insertion (with slot reservation), pause/resume flows, and bandwidth shaping all operational. Performance and responsiveness have been optimized:
- **Optimistic UI Updates**: State transitions (Pause, Resume, Done) now update the frontend stores immediately on API success, bypassing the 5-second polling state lag.
- **Grouped Authorization Calls**: During bulk coin drop processing, firewall authorization is skipped for intermediate coins and runs only on the last coin, reducing shell subprocess execution by up to 10×.
- **COUNT(*) Optimization**: ORM objects are no longer fully hydrated to check session counts in the capacity check and health endpoints, utilizing indexed SQL counts instead.
- **JOIN in Expiration check**: Fixed N+1 client lookups in session expiration background jobs using a single JOIN query.

## Complete Architecture
- **Hardware**: Ubuntu Server running the core stack, connected to an AP. An Arduino listens to a coin acceptor and transmits data over Serial.
- **Backend Flow**: FastAPI handles REST requests. Background schedulers handle session timeouts and hardware polling.
- **Frontend Flow**: React frontend served by Nginx. Polls the backend for session status or uses WebSockets/polling to update timers.
- **Database Schema**: MySQL/MariaDB with Tables for `sessions`, `clients`, `rates`, `sales`.

## Features
- **Coin Lifecycle & Reservation**: The coin acceptor is OFF by default. It activates exclusively when a user clicks "Insert Coin". The backend reserves the slot for that specific MAC address for a 30-second window. It ignores other clients (`409 Conflict`) until the reservation is released or times out.
- **Pause/Resume Lifecycle**: Users can pause their session to preserve time. `nftables` revokes internet access. Clean state transitions are synced to frontend immediately.
- **Traffic Shaping (Bandwidth Limits)**: Each authenticated client is strictly limited to 10 Mbps Download and 10 Mbps Upload using `tc` (HTB qdiscs and `ifb0` for ingress shaping).
- **Concurrent Session Limit**: The backend strictly limits active sessions to 150 to prevent kernel memory exhaustion by `tc` and `nftables` rules.
- **Sound Manager Integration**: A centralized frontend `SoundManager` handles sequential audio playback (`explosion.mp3`, `nuke-alarm.mp3`, `chicken-screaming.mp3`, `success.mp3`) based on coin insertion actions, preventing overlapping audio and responding to visibility changes. Gated behind `import.meta.env.DEV` to exclude verbose development console logs in production builds.
- **Persistent UI Actions**: The "Insert Coin" button and its modal logic are present across all views (Idle, Active, Paused, Resumed) for seamless session extensions, coexisting cleanly with Pause/Resume buttons styled as secondary glass elements.
- **Countdown Neon Glow**: The coin insertion modal border pulses dynamically in rhythm with the countdown clock using a hardware-accelerated dual-layered cyan and purple CSS box-shadow animation.

## Important Files
- `/opt/pisowifi/backend/services/bandwidth_service.py`: Critical `tc` wrapper for shaping limits.
- `/opt/pisowifi/backend/services/firewall_service.py`: `nftables` interface.
- `/opt/pisowifi/backend/services/coin_service.py`: Serial listener and reservation manager.
- `/opt/pisowifi/frontend/src/utils/SoundManager.js`: Global audio singleton.

## Design Decisions
- **Absolute Paths in Backend**: Services executing system binaries (`tc`, `ip`) use absolute paths (`/usr/sbin/tc`) to survive systemd's limited `$PATH`.
- **Exclusive Hardware Locking**: To prevent "coin theft," only one client can reserve the coin slot at a time.
- **Strict `prio 1` in `tc`**: TC filters must explicitly specify `prio 1` for reliable addition and deletion.
- **Grouped Authorization in Loops**: When releasing slots with multiple coins, only the last item runs the full authorize command to prevent thread-blocking command floods.

## Current Known Bugs / Workarounds
- **Old Android Pause Issue**: Handled by stabilizing backend session states and ensuring the frontend strictly adheres to backend statuses (`ACTIVE`, `PAUSED`).
- **Nginx direct static bypass**: Audio files in `/opt/pisowifi/sfx` are served directly via Nginx (`/api/sfx/`) bypassing the FastAPI application completely (fallback routing configured in site configuration).

## System Startup
- `lifespan` in `main.py` initializes root `tc` qdiscs and starts background scheduler jobs before accepting web requests.
