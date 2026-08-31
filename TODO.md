# TODO List

## Orange Pi PC on-device acceptance

- [ ] Run the printed relay test on the actual 5V module through a verified 3.3V-safe driver/interface.
- [ ] Calibrate every enabled denomination through the final opto-isolated pulse circuit.
- [ ] Verify relay OFF at boot, graceful stop, backend/coin-listener restart, tab crash, and Wi-Fi loss.
- [ ] Record the actual Debian 13 architecture and live gpiochip paths selected by the installer; do not pre-assume `armhf` or `/dev/gpiochip0`.

This file tracks the upcoming phases and tasks required to transition PisoWiFi into a portable production platform.

## Remaining Roadmap Phases

- [x] **Phase 2: Platform Service Abstractions**
  - Abstract network, firewall, bandwidth shaping, serial communication, and system operations behind clean service interfaces.
  - Implement mock/local drivers to facilitate developer execution and testing on non-Linux machines (Windows/macOS) without failing on missing CLI binaries.
  - Eliminate direct database transaction imports inside hardware routines.
- [x] **Phase 3: Hardware Detection**
  - Replace static interface and device heuristics with auto-detection.
  - Implement active search across system serial ports (`/dev/ttyUSB*`, `/dev/ttyS*`, `/dev/ttyAMA*`) to detect the Arduino.
  - Detect kernel modules (`sch_htb`, `ifb`) and command locations dynamically.
- [x] **Phase 4: Deployment Improvements**
  - Build an interactive installation wizard.
  - Generate Nginx, Dnsmasq, and systemd files dynamically from environment-specific templates.
- [x] **Phase 5: Diagnostics**
  - Add `/api/v1/diagnostics` for system state audit (checking file permissions, db connects, serial status, and tool availability).
- [x] **Phase 6: Remaining Low-Risk Portability Improvements**
  - Migrate reservation tracking and balance lock states from raw disk files (`/opt/pisowifi/run/`) to SQLite/database tables.
  - Support SQLite as a lightweight db engine configuration.

## Deployment & Reliability Roadmap

- [x] **Phase 1: Pre-Flight Audits, Versioning, and Database Migrations**
  - Create VERSION file tracking active release versions.
  - Set up pre-flight validators for OS version (Ubuntu >= 20.04 or Debian >= 11), Python version (>= 3.9), and kernel capabilities (`sch_htb`, `ifb`, `act_mirred`).
  - Integrate programmatic Alembic schema migrations during application boot sequence (lifespan hook).
  - Add initial migration schema script supporting conditional triggers to safely handle existing deployments without data loss.
- [x] **Phase 2: Transactional Installer, Rollback, Uninstaller, and Dry-Run**
  - Implement transactional installations back-ups for config and service files.
  - Design rollback registers to revert state on installation failures.
  - Implement `--uninstall` flags to stop/remove PisoWiFi components safely.
  - Add `--dry-run` modes to simulate installations without making disk writes.
- [x] **Phase 3: Centralized Logging and Command-Line Interface (Doctor)**
  - Integrate rotating logging handlers for installation, updates, migrations, and doctor operations.
  - Develop `pisowifi doctor` command-line utility to diagnose, troubleshoot, and output system status checkmarks.
- [x] **Phase 4: Automated Upgrades and Configuration Migrations**
  - Develop a transactional `pisowifi upgrade` command.
  - Add automated `.env` settings migration matching old/new variables.
  - Implement template version verification using MD5 hashes to protect local configuration customizations.

## Production Certification & Security Hardening

- [x] **Phase 4: Final Audit & Hardening**
  - Add weak JWT secret detection warning at startup (config.py).
  - Add service-layer USED status guard to VoucherService.delete_voucher().
  - Add input validation guards to install.py (int() conversion, service restart checks).
  - Run comprehensive production audit across installer, scripts, templates, frontend, and backend.
  - Full remediation report: /tmp/pisowifi_output/remediation_report.txt

## Performance & Optimizations

- [x] **Phase 1: Core Dashboard & Diagnostics Optimizations**
  - Implement dynamic memory-based caching (`HealthCacheService`) for all system diagnostics checks (systemctl service checks, WAN checks, DNS checks) decoupled from HTTP request thread.
  - Implement dynamic serial port path caching with disk-check validation to avoid 840ms port scanning latency.
  - Optimize database aggregations into single conditional `SUM(CASE WHEN...)` statement.
  - Implement rolling CPU calculation from `/proc/stat` to show actual CPU utilization delta.

## Voucher System Certification & Security Hardening

- [x] **Phase 1: Admin Auth & Interpolation Hardening**
  - Prevent environment variable `$` string interpolation in `load_dotenv()` (`interpolate=False`).
  - Update `.env` `ADMIN_PASSWORD_HASH` with single-quoted valid 60-character bcrypt hash for `admin123`.
  - Add explicit exception logging to `verify_password()` in [auth.py](file:///opt/pisowifi/backend/utils/auth.py).
- [x] **Phase 2: Automatic Client Registration & Test Suite**
  - Update `_process_voucher_redemption()` in [voucher.py](file:///opt/pisowifi/backend/api/v1/voucher.py) to use `ClientRepository.get_or_create()`.
  - Build automated test suite in [test_voucher_hotfix.py](file:///opt/pisowifi/backend/tests/api/test_voucher_hotfix.py) (36/36 tests passing).
- [x] **Phase 3: Production Admin Credential Management & Liquid Glass UI**
  - Implement `AdminCredentialsService` ([admin_credentials_service.py](file:///opt/pisowifi/backend/services/admin_credentials_service.py)) and `POST /api/admin/credentials` for atomic, rollback-safe `.env` credential updates.
  - Build CLI credential recovery tool ([manage.py](file:///opt/pisowifi/backend/manage.py)) supporting `check`, `set-username`, and `reset-password`.
  - Overhaul Voucher UI into Apple 2026 Liquid Glass design language and mount `AdminSettings.jsx` security tab in Dashboard.
  - Expand test suite to 38 passing tests ([test_credentials_management.py](file:///opt/pisowifi/backend/tests/api/test_credentials_management.py)).

