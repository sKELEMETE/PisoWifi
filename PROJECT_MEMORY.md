# Project Memory

## Current Project Status
The project is fully functional and production-ready. The captive portal, session lifecycle, coin insertion (with slot reservation), pause/resume flows, and bandwidth shaping are all operational and highly optimized:
- **Optimistic UI Updates**: State transitions (Pause, Resume, Done) update the frontend stores immediately on API success, bypassing the 5-second polling state lag.
- **Grouped Authorization Calls**: During bulk coin drop processing, firewall authorization is skipped for intermediate coins and runs only on the last coin, reducing shell subprocess execution by up to 10×.
- **COUNT(*) Optimization**: ORM objects are no longer fully hydrated to check session counts in the capacity check and health endpoints, utilizing indexed SQL counts instead.
- **JOIN in Expiration check**: Fixed N+1 client lookups in session expiration background jobs using a single JOIN query.
- **Reliability & Traffic Control Enhancements**:
  - `TC-01`: Replaced generic `tc filter del` commands with explicit handles (`800::{cid:x}`) derived from client class IDs. This stops system deletions from flusher-flushing the packet classification filters of all other active clients.
  - `R-01`: Startup Sequence waits for MariaDB connection, performs power recovery (pauses active sessions), and rebuilds firewall state on boot.
  - `R-02`: Persistent coin transaction files stored in `/opt/pisowifi/run/` with automated startup reconciliation.
  - `R-03`: Declarative Firewall State Auditor periodically reconciles `nftables` sets with active database sessions every 30s. Fixed a critical scheduler crash where an undefined module-level `logger` threw `NameError` and aborted sync loops.
  - `R-04`: Dynamic client IP migrations automatically update firewall and shaping rules on DHCP renewals.
  - `R-05`: Monotonic clock jump monitor compensates active session `end_time` limits if NTP sync occurs.
- **Robust Session Restoration**: Fixed Landing Page flash/UI flicker by dynamically returning users to their correct previous status (Active/Paused) immediately upon closing the coin pop-up.
- **Time Terminology Update**: Replaced all user-facing instances of "Session" with "Time" throughout the client portal for clean and simple user communication.
- **Single Scrollable Card Layout**: Redesigned the portal wrapper so the entire portal card scrolls as a single unified container under one custom thin scrollbar. Replaced nested scrolls and removed the footer to maximize viewport real estate on mobile devices.

## Complete Architecture
- **Hardware**: Ubuntu Server running the core stack, connected to an AP. An Arduino listens to a coin acceptor and transmits data over Serial.
- **Backend Flow**: FastAPI handles REST requests. Background schedulers handle session timeouts and hardware polling.
- **Frontend Flow**: React frontend served by Nginx. Polls the backend for session status or uses WebSockets/polling to update timers.
- **Database Schema**: MySQL/MariaDB with Tables for `sessions`, `clients`, `rates`, `sales`, `vouchers`.
  - Added `pause_allowed` column to `sessions` table to restrict pause features.

## Pricing Model (₱1 - ₱20)
- **Accumulated Peso-Based Pricing**: Pricing is calculated ONLY from the total accumulated peso amount inserted during a single reservation slot:
  - ₱1 = 20m, ₱2 = 40m, ₱3 = 1h, ₱4 = 1h 20m, ₱5 = 3h, ₱6 = 3h 20m, ₱7 = 3h 40m, ₱8 = 4h, ₱9 = 4h 20m, ₱10 = 6h, ₱11 = 6h 20m, ₱12 = 6h 40m, ₱13 = 7h, ₱14 = 7h 20m, ₱15 = 10h, ₱16 = 10h 20m, ₱17 = 10h 40m, ₱18 = 11h, ₱19 = 11h 20m.
  - ₱20 = 24h package which sets `pause_allowed = false` (rejects Pause requests via backend, hides Pause button on frontend, and renders a "Not Pausable" caption in the pricing table).
- **Backend Driven**: The rates and durations are fetched dynamically from the database using the `/pricing` endpoint. The frontend remains free of hardcoded rates or durations.

## Features
- **Coin Lifecycle & Reservation**: The coin acceptor is OFF by default. It activates exclusively when a user clicks "Insert Coin". The backend reserves the slot for that specific MAC address for a 30-second window.
- **Pause/Resume Lifecycle**: Users can pause their session to preserve time. `nftables` revokes internet access.
- **Traffic Shaping (Bandwidth Limits)**: Each authenticated client is strictly limited to 10 Mbps Download and 10 Mbps Upload using `tc` (HTB qdiscs and `ifb0` for ingress shaping).
- **Concurrent Session Limit**: The backend strictly limits active sessions to 150 to prevent kernel memory exhaustion by `tc` and `nftables` rules.
- **Sound Manager Integration**: A centralized frontend `SoundManager` handles sequential audio playback (`explosion.mp3`, `nuke-alarm.mp3`, `chicken-screaming.mp3`, `success.mp3`) based on coin insertion actions, preventing overlapping audio and responding to visibility changes.
- **Persistent UI Actions**: The "Insert Coin" button and its modal logic are present across all views (Idle, Active, Paused, Resumed) for seamless session extensions.
- **Countdown Neon Glow**: The coin insertion modal border pulses dynamically in rhythm with the countdown clock using a hardware-accelerated dual-layered cyan and purple CSS box-shadow animation.

## Important Files
- `/opt/pisowifi/backend/services/bandwidth_service.py`: Critical `tc` wrapper for shaping limits.
- `/opt/pisowifi/backend/services/firewall_service.py`: `nftables` interface.
- `/opt/pisowifi/backend/services/coin_service.py`: Serial listener and reservation manager.
- `/opt/pisowifi/frontend/src/utils/SoundManager.js`: Global audio singleton.
- `/opt/pisowifi/frontend/src/config/branding.js`: Centralized dynamic branding file mapping environment variables.

## Design Decisions
- **Absolute Paths in Backend**: Services executing system binaries (`tc`, `ip`) use absolute paths (`/usr/sbin/tc`) to survive systemd's limited `$PATH`.
- **Exclusive Hardware Locking**: To prevent "coin theft," only one client can reserve the coin slot at a time.
- **Strict `prio 1` in `tc`**: TC filters must explicitly specify `prio 1` for reliable addition and deletion.
- **Grouped Authorization in Loops**: When releasing slots with multiple coins, only the last item runs the full authorize command to prevent thread-blocking command floods.
- **Explicit Filter Handles**: Explicit handles (`800::{cid:x}`) are used when adding and deleting u32 filters to isolate changes to target clients.
- **Scroll Container Architecture**: A single scrollable card layout is used with `overflow-y: auto` to prevent nested scrollbars and ensure clean, unified page scaling on mobile.

## Current Known Bugs / Workarounds
- **Old Android Pause Issue**: Handled by stabilizing backend session states and ensuring the frontend strictly adheres to backend statuses (`ACTIVE`, `PAUSED`).
- **Nginx direct static bypass**: Audio files in `/opt/pisowifi/sfx` are served directly via Nginx (`/api/sfx/`) bypassing the FastAPI application completely.

## System Startup
- `lifespan` in `main.py` initializes root `tc` qdiscs, runs `StartupSequence` recovery, auto-seeds/updates rates database tables, and starts background scheduler jobs before accepting web requests.
