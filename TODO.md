# TODO List

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
- [ ] **Phase 4: Automated Upgrades and Configuration Migrations**
  - Develop a transactional `pisowifi upgrade` command.
  - Add automated `.env` settings migration matching old/new variables.
  - Implement template version verification using MD5 hashes to protect local configuration customizations.

