# Changelog

All notable changes to the PisoWiFi project will be documented in this file.

## [1.14.0] - 2026-07-21

### Added
- **Weak JWT Secret Detection**: Added startup warning in [config.py](file:///opt/pisowifi/backend/config.py) that detects common weak/default JWT secrets and low-entropy patterns.
- **Voucher USED Status Protection**: Added service-layer guard in [voucher_service.py](file:///opt/pisowifi/backend/services/voucher_service.py) preventing deletion of vouchers with USED status, with API-level defense-in-depth in [admin_voucher.py](file:///opt/pisowifi/backend/api/v1/admin_voucher.py).
- **install.py Hardening**: Added try/except guards around port input `int()` conversion to prevent `ValueError` crashes. Added return-code checking for systemd service restarts with per-service failure reporting.

### Fixed
- **Production Certification Remediation**: Resolved all issues from the final production audit. All 38 tests passing. Full report at `/tmp/pisowifi_output/remediation_report.txt`.

## [1.13.0] - 2026-07-21

### Added
- **Apple 2026 Liquid Glass Voucher UI Redesign**: Redesigned captive portal voucher redemption (`VoucherForm.jsx`) with pill-shaped glass inputs, loading states, and accessible status banners. Fully overhauled admin voucher management (`VoucherManagement.jsx`) with Apple Liquid Glass stat cards, filter controls, sticky glass headers, pagination, and scale-animated glass modal dialogs.
- **Admin Credential Management Workflow**: Added `AdminCredentialsService` ([admin_credentials_service.py](file:///opt/pisowifi/backend/services/admin_credentials_service.py)) and `POST /api/admin/credentials` endpoint supporting atomic, rollback-safe username and password updates without manually editing `.env`.
- **CLI Credential Recovery Tool**: Created [manage.py](file:///opt/pisowifi/backend/manage.py) supporting `credentials check`, `set-username`, and `reset-password` operations.
- **Admin Security Settings UI**: Built [AdminSettings.jsx](file:///opt/pisowifi/frontend/src/components/admin/AdminSettings.jsx) with Liquid Glass credential management forms that automatically invalidate active sessions and force re-login upon credential changes.
- Created comprehensive regression test suite in `backend/tests/api/test_credentials_management.py` (38/38 tests passing).

### Fixed
- **Admin Authentication Hardening**: Enforced bcrypt-only runtime authentication in [auth.py](file:///opt/pisowifi/backend/utils/auth.py), removing plaintext fallback (`PLAINTEXT_MODE`).
- **Fail-Fast Startup Validation**: Added startup validation in [config.py](file:///opt/pisowifi/backend/config.py) enforcing `ADMIN_USERNAME` (min 3 chars), valid bcrypt hash dry-run check, `ADMIN_JWT_SECRET` (min 16 chars), and positive token expiration. Refuses startup on invalid configurations.
- **JWT & Cookie Hardening**: Injected `iat` (issued-at) claim into signed access tokens, enforced `algorithms=["HS256"]` and claim verification, and standardized explicit `path="/"` on auth cookies.
- **Dashboard 401 Error Interceptor**: Added HTTP 401 response interceptor in [adminClient.js](file:///opt/pisowifi/frontend/src/api/adminClient.js) and refined [AdminDashboard.jsx](file:///opt/pisowifi/frontend/src/components/admin/AdminDashboard.jsx) to distinguish 401 unauthorized states from network connectivity failures.

## [1.12.0] - 2026-07-18

### Added
- Deployed a thread-safe `HealthCacheService` memory cache to hold system diagnostics.
- Mounted an asynchronous background task runner in `main.py` lifespan to refresh health diagnostics in a background thread every 30 seconds.
- Implemented thread-safe caching of the auto-detected serial port in `detect_serial_device()`, reducing consecutive check times from 840ms to <0.1ms.
- Implemented actual rolling CPU usage percent calculation using tick deltas from `/proc/stat`.
- Configured the frontend admin dashboard to poll every 15 seconds (reduced from 5 seconds) and changed the DNS label from "Resolving" to "DNS Online".

### Changed
- Refactored the `/api/admin/dashboard` endpoint to serve system health metrics directly from `HealthCacheService` without blocking diagnostic executions.
- Consolidated the three sales aggregation queries into a single database SQL statement utilizing conditional `SUM(CASE WHEN...)` aggregation, dropping sales query execution latency by 95%.

## [1.11.0] - 2026-07-18

### Added
- Deployed dynamic systemctl command resolution in diagnostics health audits.
- Implemented MAC Randomization session migration in `get_current_client`.
- Added Cache-Control response headers middleware to all `/api/` endpoints to prevent browser and Captive Portal WebView caching.
- Integrated query parameter cache busting in frontend `getSession` and `getClient` API fetch queries.

### Fixed
- Fixed Uvicorn restricted environment path failures resolving system tools (`tc`, `ip`, `modprobe`).
- Fixed Admin Panel dotenv loading priorities and fallback credentials checks.
- Fixed startup recovery power sequence pausing active sessions on backend restarts (treating them as reboots only if host uptime is < 120s).
- Fixed database session transaction rollbacks by resolving the uncommitted `Sale` Session ID association and deferring firewall authorizations until after database commits successfully complete.
- Hardened Active Clients layout design in Admin Dashboard styling.

## [1.1.0] - 2026-07-16

### Added
- Phase 1 of Portability Roadmap: Centralized machine-specific configuration parameters.
- Added `PISOWIFI_BASE_DIR` environment variable to configure the project's root path.
- Added `PISOWIFI_RUN_DIR` environment variable to customize runtime lock and status files location.
- Added `SFX_DIRECTORY` environment variable to configure custom static sound effects paths.
- Added custom command path overrides `PATH_NFT`, `PATH_TC`, `PATH_IP`, and `PATH_MODPROBE` to allow running the backend on distributions with different system tool layouts.
- Added network and interface parameters `PISOWIFI_GATEWAY_IP`, `PISOWIFI_SUBNET_CIDR`, and `PISOWIFI_LAN_INTERFACE_FALLBACK` for deployment across varying subnets.
- Centralized `COIN_RESERVATION_TIMEOUT` and bandwidth shaper limits `PISOWIFI_BANDWIDTH_RATE` and `PISOWIFI_BANDWIDTH_CEIL`.

### Changed
- Configured [bandwidth_service.py](file:///opt/pisowifi/backend/services/bandwidth_service.py) to read binary tools, bandwidth rates, and fallback interface names from config.
- Configured [firewall_service.py](file:///opt/pisowifi/backend/services/firewall_service.py) and [jobs.py](file:///opt/pisowifi/backend/scheduler/jobs.py) to dynamically construct `nft` commands using centralized settings.
- Updated [coin_listener.py](file:///opt/pisowifi/backend/coin_serial/coin_listener.py), [coin.py](file:///opt/pisowifi/backend/api/v1/coin.py), and [startup_sequence.py](file:///opt/pisowifi/backend/recovery/startup_sequence.py) to dynamically map lockfiles and pending coin drop storage under the centralized run directory path.
- Updated static assets directory in [main.py](file:///opt/pisowifi/backend/main.py) to read from configured `SFX_DIRECTORY`.

## [1.2.0] - 2026-07-16

### Added
- Phase 2 of Portability Roadmap: Platform Service Abstractions.
- Added platform abstraction drivers (`FirewallDriver`, `BandwidthDriver`, `NetworkProvider`, `SerialPortDriver`) to decouple business logic from OS command invocation and direct package imports.
- Added `PISOWIFI_FIREWALL_DRIVER`, `PISOWIFI_BANDWIDTH_DRIVER`, `PISOWIFI_NETWORK_PROVIDER`, and `PISOWIFI_SERIAL_DRIVER` environment variable settings.
- Implemented `MockFirewallDriver`, `MockBandwidthDriver`, `MockNetworkProvider`, and `MockSerialReader` for full platform-independent execution and testing (on macOS/Windows).
- Configured `PISOWIFI_BACKEND_PORT` to configure the API port dynamically.

### Changed
- Refactored [firewall_service.py](file:///opt/pisowifi/backend/services/firewall_service.py) to utilize pluggable drivers, allowing Nftables or Mock executions.
- Refactored [bandwidth_service.py](file:///opt/pisowifi/backend/services/bandwidth_service.py) to separate Linux traffic control (`tc`) shaper from Mock implementation.
- Refactored [network_service.py](file:///opt/pisowifi/backend/services/network_service.py) to use pluggable MAC providers, decoupling ARP reading.
- Refactored [serial_reader.py](file:///opt/pisowifi/backend/coin_serial/serial_reader.py) and [serial_manager.py](file:///opt/pisowifi/backend/coin_serial/serial_manager.py) to support mock serial port readers to avoid 100% CPU lockups in simulated developer environments.
- Eliminated direct database dependencies and transactions inside [coin_listener.py](file:///opt/pisowifi/backend/coin_serial/coin_listener.py#L102) by replacing the watchdog bulk coin finalization loop with a local API call to the `/release` REST endpoint.

## [1.3.0] - 2026-07-16

### Added
- Phase 3 of Portability Roadmap: Hardware & Binary Auto-detection.
- Implemented robust serial device auto-detection logic in [device_detector.py](file:///opt/pisowifi/backend/coin_serial/device_detector.py): scans USB devices, ACM ports, and common hardware SBC serial UARTs (`/dev/ttyAMA0`, `/dev/ttyS0`).
- Implemented dynamic CLI system tools auto-detection using `shutil.which` in [config.py](file:///opt/pisowifi/backend/config.py), eliminating absolute-only tool paths.
- Added dynamic capability checks and warning logs for missing tool commands (`nft`, `tc`, `ip`, `modprobe`) in services setup/initialization.

## [1.4.0] - 2026-07-16

### Added
- Phase 4 of Portability Roadmap: Deployment & Installation Wizard.
- Created dynamic deployment configuration templates:
  - `pisowifi-backend.service.template` (Systemd API Service)
  - `pisowifi-coin.service.template` (Systemd Coin daemon)
  - `nginx.conf.template` (Nginx captive portal server config)
  - `dnsmasq.conf.template` (Dnsmasq DHCP/DNS gateway config)
  - `nftables.conf.template` (Nftables base firewall table and sets config)
- Developed an interactive python deployment wizard `install.py` supporting auto-detected defaults (interface, routing), prompts, validation, and a non-interactive mode.
- Added support for generating custom environment files (`.env`) dynamically during installation.

## [1.5.0] - 2026-07-16

### Added
- Phase 5 of Portability Roadmap: System Diagnostics API.
- Implemented `/api/v1/diagnostics` GET endpoint in [diagnostics.py](file:///opt/pisowifi/backend/api/v1/diagnostics.py) to audit system health state.
- Diagnostics includes:
  - Database connectivity (tested using SQLAlchemy wrapped `SELECT 1` queries).
  - Runtime filesystem permissions (checking if run directory `/opt/pisowifi/run` exists and is writable).
  - Network and system binary availability (checking existence and executability for `nft`, `tc`, `ip`, and `modprobe`).
  - Serial connection status (verifying serial device presence or mock state).

### Changed
- Registered `diagnostics_router` inside [api/v1/api.py](file:///opt/pisowifi/backend/api/v1/api.py).

## [1.10.0] - 2026-07-16

### Added
- Phase 4 of Production Deployment Roadmap: Automated Upgrades, Configuration Migrations, and Template Versioning.
- Implemented a transactional upgrade workflow module (`installer/upgrade.py`) executed via `pisowifi upgrade` that performs:
  - Automated configuration backup validations before starting.
  - Interactive/headless `.env` settings migration matching old and new variables.
  - MD5 hash checking on active files (`/etc/`) to verify and protect custom administrator edits from silent overwrites.
  - Programmatic database migrations using Alembic and post-upgrade diagnostic validation audits.
  - Safe system rollbacks upon failure.
- Developed `tests/test_upgrade.py` verifying environmental migrations and file MD5 customization checks.

### Changed
- Integrated the `upgrade` subcommand into [cli.py](file:///opt/pisowifi/installer/cli.py) CLI parser.

## [1.9.2] - 2026-07-16

### Added
- Implemented robust scored-candidate serial port detection and active handshake probing in [device_detector.py](file:///opt/pisowifi/backend/coin_serial/device_detector.py):
  - Scans and ranks comports using target VID/PID signatures (e.g. FTDI `0403:6001`, CH340, CP210x, Arduino).
  - Probes candidate ports for active PisoWiFi coin selector handshake signatures (`PISOWIFI`, `PULSES`, `COIN`) before fallback.
  - Recovers and connects dynamically to re-mapped interfaces (e.g. `/dev/ttyUSB1` after USB unplug/replug relocation).
- Added root logging configuration in [run_coin_listener.py](file:///opt/pisowifi/backend/run_coin_listener.py) and added pipeline validation/dispatch events logging in [coin_listener.py](file:///opt/pisowifi/backend/coin_serial/coin_listener.py) to eliminate silent failures.

### Changed
- Configured `/opt/pisowifi/.env` to default to `SERIAL_PORT=AUTO` to enable dynamic serial detection out of the box.

## [1.9.1] - 2026-07-16

### Fixed
- Fixed critical production regression in [coin_listener.py](file:///opt/pisowifi/backend/coin_serial/coin_listener.py):
  - Corrected `Debouncer` class instantiation to use the parameterless constructor (`Debouncer()`) instead of passing the unexpected `delay_ms` argument.
  - Replaced the call to the non-existent `.debounce()` method with `.allow()`, matching the correct method implementation in [debounce.py](file:///opt/pisowifi/backend/coin_serial/debounce.py).

## [1.9.0] - 2026-07-16

### Added
- Phase 3 of Production Deployment Roadmap: CLI framework, Doctor command, and Central logging.
- Created `bin/pisowifi` bash wrapper and `installer/cli.py` script forming a dynamic command CLI system linked to `/usr/local/bin/pisowifi`.
- Implemented `installer/doctor.py` introducing a comprehensive system checkups suite (`pisowifi doctor`) verifying database, backend API, network interfaces, firewall, traffic shaping (`tc`), system services, and internet access, classifying alerts into Critical/Warning/Healthy states.
- Implemented `installer/log_manager.py` setting up centralized rotating log handlers that track installation (`install.log`), rollbacks (`rollback.log`), migrations (`migration.log`), updates, and doctor execution events.

### Changed
- Refactored [install.py](file:///opt/pisowifi/install.py) to link and install the CLI manager to `/usr/local/bin/pisowifi` and write logs to the central logging directory `/opt/pisowifi/logs/`.
- Configured [main.py](file:///opt/pisowifi/backend/main.py#L31) to record programmatic database migrations details directly to `logs/migration.log`.

## [1.8.0] - 2026-07-16

### Added
- Phase 2 of Production Deployment Roadmap: Transactional installer, backup validation, dry-run, and uninstaller.
- Implemented `installer/rollback.py` introducing a `RollbackManager` that tracks all file creations, link operations, and overrides during installation to revert changes in reverse order if a failure occurs.
- Implemented `installer/backup.py` introducing pre-install validation backups. Automatically backing up and validating the integrity of existing configuration assets (`.env`, system files, templates) before modifications start.
- Implemented `installer/uninstall.py` supporting a clean, automated uninstallation of Nginx, Dnsmasq, and systemd units while optionally preserving user data or database assets.
- Integrated `--dry-run` and `--uninstall` command options inside the main `install.py` wizard.

### Changed
- Refactored [installer/templates.py](file:///opt/pisowifi/installer/templates.py) to execute system file operations transactionally via the `RollbackManager`.

## [1.7.0] - 2026-07-16

### Added
- Phase 1 of Production Deployment Roadmap: Version management and Alembic migrations.
- Added a `VERSION` file tracking active release versions.
- Added a structured `installer/` directory for refactored install tooling.
- Implemented `installer/utils.py` for common helper utilities and root verification.
- Implemented `installer/validate.py` running automated checks for OS release versions (Ubuntu >= 20.04 or Debian >= 11) and Python versions (>= 3.9).
- Implemented kernel module capability validations checking for `sch_htb`, `ifb`, and `act_mirred` module availability.
- Integrated programmatic Alembic migrations in [main.py](file:///opt/pisowifi/backend/main.py#L29) lifespan, executing `alembic upgrade head` dynamically.
- Developed an initial Alembic schema migration script (`fffa6e27566e_initial_schema.py`) with conditional table check triggers to safely handle existing deployments without regression or data loss.

### Changed
- Refactored [install.py](file:///opt/pisowifi/install.py) to run pre-flight system compatibility checks and consume modular utilities from the `installer/` directory.

## [1.6.0] - 2026-07-16

### Added
- Phase 6 of Portability Roadmap: SQLite support & Database reservation migration.
- Added database tables `coin_reservations` and `pending_coins` using SQLAlchemy models `CoinReservation` and `PendingCoin` to persist client coin insertions in DB tables, replacing files `active_mac.txt`, `pending_coin.txt`, and `session_coins_{mac}.json` in `/opt/pisowifi/run`.
- Implemented `POST /api/v1/coin/insert` API endpoint for the serial listener daemon to record coin drop events without needing local file lock privileges.
- Added support for SQLite databases, allowing the entire application stack to be run in a single SQLite database file (`PISOWIFI_DATABASE_TYPE=sqlite`).
- Added dynamic, idempotent table creation on app startup (`Base.metadata.create_all`) for both MySQL and SQLite engines.

### Changed
- Refactored [database.py](file:///opt/pisowifi/backend/database.py) to read `DATABASE_URL` configurations and dynamically apply SQLite specific settings (e.g. `check_same_thread`).
- Overhauled [coin_listener.py](file:///opt/pisowifi/backend/coin_serial/coin_listener.py) to act as a stateless serial listener bridge.
- Refactored [startup_sequence.py](file:///opt/pisowifi/backend/recovery/startup_sequence.py) to reconcile pending coins on startup directly from the database table.
- Configured [jobs.py](file:///opt/pisowifi/backend/scheduler/jobs.py) scheduler to expire reservations automatically in the background.





