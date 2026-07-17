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
- **Portability Configuration Centralization (Phase 1)**: Centralized all machine-specific settings (tool command paths `nft`/`tc`/`ip`/`modprobe`, base and run directory locations, gateway IPs, subnet mask configurations, and fallback interface names) inside [config.py](file:///opt/pisowifi/backend/config.py) utilizing environment overrides with backwards-compatible fallbacks.
- **Platform Service Abstractions (Phase 2)**: Refactored `FirewallService`, `BandwidthService`, `NetworkService`, and `SerialManager` to delegate operations to pluggable interface drivers (`FirewallDriver`, `BandwidthDriver`, `NetworkProvider`, `SerialPortDriver`), introducing `Mock` implementations for multi-platform local development. Eliminated direct database dependencies inside hardware listener scripts by routing timeout notifications through loopback API endpoints.
- **Hardware & Binary Path Auto-Detection (Phase 3)**: Implemented runtime lookup utilizing `shutil.which` to find `nft`/`tc`/`ip` locations dynamically. Developed smart serial port discovery in [device_detector.py](file:///opt/pisowifi/backend/coin_serial/device_detector.py) matching USB/ACM/Arduino profiles and common SBC hardware UART ports (`/dev/ttyAMA0`, `/dev/ttyS0`), and integrated startup capability verification logs.
- **Deployment Dynamic Configurations (Phase 4)**: Created templates for Systemd, Nginx, Dnsmasq, and Nftables configurations. Developed an interactive/headless deployment python script `install.py` that auto-detects host network routing configurations, compiles deployment template settings, creates backend configurations, and installs site services to `/etc/` system directories.
- **System Diagnostics Monitoring (Phase 5)**: Developed `/api/v1/diagnostics` API endpoint in [diagnostics.py](file:///opt/pisowifi/backend/api/v1/diagnostics.py) to run complete system audits (SQLAlchemy database connectivity tests, filesystem permission checks, Linux system tool existence/execution permissions, and active/mock serial port connectivity states).
- **SQLite Support & DB Reservation Tracking (Phase 6)**: Migrated coin acceptor slot reservations and pending balances to `coin_reservations` and `pending_coins` database tables, removing raw disk file lock dependencies. Integrated SQLite engine support with automatic startup table generation. Overhauled the serial listener script to act as a stateless HTTP REST bridge, and migrated reservation inactivity timeouts to background scheduler jobs.
- **Coin Listener Debouncer Hotfix**: Fixed a production crash in the hardware coin listener daemon by resolving class initialization parameter mismatches and aligning debouncer checks with the correct `.allow()` utility methods.
- **Scored Serial AUTO Detection & Logging Visibility**: Fixed USB serial port remapping failure and silent execution bugs by implementing scored FTDI/Arduino USB port detection, active PisoWiFi handshake signature probing, root logging config, and pipeline validation trace logs.
- **Automated Upgrades, Environment Migration & MD5 Hash Verification (Deployment Phase 4)**: Implemented `pisowifi upgrade` command supporting pre-upgrade backup verification, automated environment variable migrations, MD5 configuration hash checking to save backups of manual customization files, programmatic Alembic upgrades, and post-upgrade health validation.
- **Pre-Flight Validation & Alembic Migrations (Deployment Phase 1)**: Integrated dynamic versioning (`VERSION`), pre-flight compatibility checkers (Python ver, OS distro, and kernel module queuing capability audits), and integrated Alembic schema migrations running programmatically on application lifespan boot.
- **Transactional Installer & Rollback Manager (Deployment Phase 2)**: Added a transactional installer layer (`RollbackManager`) that tracks system modifications (file writes, link operations, and template copy processes) and rolls them back in reverse order on failure. Integrated pre-install configuration validation backups, dry-run simulation capabilities, and a full system uninstaller.
- **CLI Framework, Doctor Command & Rotating Logs (Deployment Phase 3)**: Developed the `pisowifi` CLI command tool to run comprehensive system audits (`pisowifi doctor`) classifying system states. Structured rotating logs were centralized under `/opt/pisowifi/logs/` separating `install.log`, `rollback.log`, `migration.log`, and `doctor.log`.
- **Single Scrollable Card Layout**: Redesigned the portal wrapper so the entire portal card scrolls as a single unified container under one custom thin scrollbar. Replaced nested scrolls and removed the footer to maximize viewport real estate on mobile devices.
- **Admin Panel Production Hardening & Regression Fixes**:
  - Implemented dynamic path lookup for system commands (`tc`, `ip`, `modprobe`, `systemctl`) using `shutil.which` to bypass systemd restricted environments.
  - Implemented layered environment config loading to support system `/opt/pisowifi/.env` and project-local `backend/.env`.
  - Added MAC Randomization session migration: rebinding existing active database sessions on reconnected devices using the same leased IP.
  - Deferred firewall authorizations and notifications until after successful database transaction commits, ensuring database and firewall state consistency.
  - Appended Cache-Control headers to API responses and query cache-busters to frontend fetches to prevent captive portal WebView caching.
  - Hardened active clients layout design in Admin Dashboard styling.

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
