# Architectural Design Decisions

This document logs significant architectural design decisions made during the evolution of the PisoWiFi platform.

## [2026-07-16] Centralized Environment Configuration (Phase 1)

### Context
To make PisoWiFi run portably across multiple hardware architectures (Orange Pi, Raspberry Pi, VMs) and differing Linux distributions (Ubuntu, Debian), we need to extract hardcoded system paths, commands, interface names, and timeouts out of service classes.

### Decision
We centralize all system-specific variables in [config.py](file:///opt/pisowifi/backend/config.py) using `os.getenv` with standard backward-compatible defaults.
- **Base/Run Directory**: Set up `PISOWIFI_BASE_DIR` defaulting to `/opt/pisowifi` and `PISOWIFI_RUN_DIR` defaulting to `/opt/pisowifi/run`. This maintains full compatibility with existing lock files and avoids breaking existing installations.
- **Network Interface**: Fallback interface configured via `PISOWIFI_LAN_INTERFACE_FALLBACK` defaulting to `"enxc817f552a5c6"`.
- **Command Overrides**: Paths to critical binary commands (`nft`, `tc`, `ip`, `modprobe`) are loaded from environment variables with standard paths.
- **Timeouts & shaping**: The shaper rate (`BANDWIDTH_RATE`) and coin reservation timeout (`COIN_RESERVATION_TIMEOUT`) are exposed.

### Consequences
- Existing deployments will continue to run without changes, as the default fallback values match the original hardcoded strings exactly.
- Porting to a new distro or folder layout can now be achieved solely by editing the environment configurations in the `.env` file without modifying source files.
- The unit testing suite continues to run successfully since all default configurations are preserved.
- **Time Terminology Update**: Replaced all user-facing instances of "Session" with "Time" throughout the client portal for clean and simple user communication.

## [2026-07-16] Platform Service Abstractions & Mock Drivers (Phase 2)

### Context
To support multi-platform deployment (Ubuntu, Debian, Raspberry Pi, VMs) and cross-platform developer support (Windows, macOS), we must prevent direct Unix shell system calls (`nft`, `tc`, `ip`) and hardware-specific package imports (serial ports) from executing blindly inside core business classes.

### Decision
We introduce abstract platform interfaces and pluggable driver factories for system operations:
- **Abstract Service Drivers**: Refactored `FirewallService`, `BandwidthService`, `NetworkService`, and `SerialManager` to delegate operations to pluggable interface drivers (`FirewallDriver`, `BandwidthDriver`, `NetworkProvider`, `SerialPortDriver`).
- **Mock Implementations**: Created `MockFirewallDriver`, `MockBandwidthDriver`, `MockNetworkProvider`, and `MockSerialReader` that execute on Windows/macOS without triggering missing tool command exceptions.
- **Optional fcntl**: Wrapped all `fcntl` Unix-only library locks in check blocks to avoid crashes on Windows.
- **REST Watchdog Finalization**: Replaced all direct database repository imports and session creation operations in [coin_listener.py](file:///opt/pisowifi/backend/coin_serial/coin_listener.py#L102) with a local loopback HTTP call to the backend `/release` endpoint.

### Consequences
- PisoWiFi can now be run, tested, and fully mocked on any macOS/Windows environment without any code edits or virtual machine setups.
- Business logic is completely decoupled from system-specific tools and daemon operations.

## [2026-07-16] Hardware & Binary Path Auto-Detection (Phase 3)

### Context
Running the platform on diverse Linux SBC boards (Orange Pi, Raspberry Pi) and various operating systems requires detecting the correct hardware interface devices and Linux CLI program locations dynamically, avoiding strict single-machine assumptions.

### Decision
We implement runtime auto-detection logic for system tools and serial port devices:
- **Dynamic Binary Lookup**: Configured `config.py` to use `shutil.which` to find `nft`, `tc`, `ip`, and `modprobe` in the system `$PATH` automatically on application startup, returning config overrides as fallbacks.
- **Enhanced Serial Auto-Detection**: Refactored `detect_serial_device` in [device_detector.py](file:///opt/pisowifi/backend/coin_serial/device_detector.py) to prioritize:
  1. Configured port path overrides (e.g. `SERIAL_PORT`).
  2. Ports matching description filters (`USB`, `ACM`, `Arduino`).
  3. Common Raspberry/Orange Pi UART serial paths (`/dev/ttyAMA0`, `/dev/ttyS0`) that exist on the filesystem.
  4. First available comport.
- **Dynamic Capability Warnings**: Added checks in `firewall_service.py` and `bandwidth_service.py` constructors to log errors if required tools (`nft`, `tc`) are not installed on the system, preventing silent failures.

### Consequences
- Hardware UARTs on Raspberry/Orange Pi SBCs are now dynamically auto-detected and supported out of the box.
- The platform automatically works on custom Linux distributions where network commands live under `/sbin` or `/usr/bin` rather than `/usr/sbin`.

## [2026-07-16] Dynamic Deployment Configuration & Installation Wizard (Phase 4)

### Context
To deploy PisoWiFi on differing hardware configurations (such as Raspberry Pi, Orange Pi, Intel Mini PCs, VMs) and varying interface names, we need a way to generate configuration files dynamically, avoiding manual setup file edits.

### Decision
We introduce template configurations and a python installation wizard script:
- **Environment-Specific Templates**: Created templates for Systemd services, Nginx configurations, Dnsmasq, and Nftables under `config/`.
- **Interactive Python Installer**: Created `install.py` in the base directory that detects system interfaces and router configurations, prompts the user interactively (or accepts CLI flags for headless/automated script runs), builds the configuration parameters, and compiles templates.
- **System Integration**: The script compiles environment files and copies configuration files directly to `/etc` folders when run as root with system reload commands.

### Consequences
- System configurations (Nginx ports, network interfaces, IP subnets, directories) are now fully generated dynamically without manual file overrides.
- Production setup is simplified to a single command: `sudo python3 install.py --non-interactive --write-system-configs`.

## [2026-07-16] System State Diagnostics Endpoint (Phase 5)

### Context
To support production management across multiple hardware architectures, admins need a simple, single point of monitoring that audits the system state, validates local file system permissions, checks database health, verifies serial port activity, and checks binary paths.

### Decision
We introduce `/api/v1/diagnostics` GET endpoint in [diagnostics.py](file:///opt/pisowifi/backend/api/v1/diagnostics.py):
- **DB Connection**: Executes SQLAlchemy `text("SELECT 1")` statements to test DB connection.
- **Filesystem Permissions**: Checks existence and write access (`os.access`) for the centralized run directory (`config.RUN_DIR`).
- **Binary Tool Availability**: Validates existence and execution permissions (`os.X_OK`) for standard Linux binaries (`nft`, `tc`, `ip`, `modprobe`).
- **Serial Connection State**: Detects if active serial connections or mock configurations exist on the server.

### Consequences
- Admins can now audit the entire deployment status of the PisoWiFi router using a single API endpoint.
- Diagnostics validation isolates DB syntax issues (e.g., SQLAlchemy 2.0 raw query warnings) before production rollouts.

## [2026-07-16] SQLite Support & Database Reservation Migration (Phase 6)

### Context
To support lightweight developer environments (avoiding MySQL/MariaDB server setups) and eliminate local file system lock dependencies, we need to migrate reservation tracking and balance lock states to database tables and allow SQLite as a pluggable database engine.

### Decision
We overhaul database engine configuration and reservation tracking:
- **Pluggable SQLite support**: Configured `config.py` and `database.py` to support `PISOWIFI_DATABASE_TYPE=sqlite` using a lightweight file `pisowifi.db`. Connect arguments are modified to avoid multi-thread transaction errors, and all tables are created dynamically at application startup.
- **SQLAlchemy Migration**: Created `CoinReservation` and `PendingCoin` tables to replace `active_mac.txt` and `session_coins_{mac}.json` lockfiles.
- **Stateless Hardware Listener**: Refactored the serial `coin_listener.py` daemon to operate as a completely stateless serial-to-REST bridge, communicating with the backend API via HTTP loopbacks.
- **Background Expiration**: Integrated timed-out slot reservation finalization inside the background scheduler (`jobs.py`).

### Consequences
- The platform runs without writing state files to `/opt/pisowifi/run/`.
- Developers can run the entire system on macOS, Linux, or Windows using SQLite without setting up any MariaDB databases.

## [2026-07-16] Alembic Integration & Version compatibility Validation (Phase 1)

### Context
To transition the captive portal backend to a production-grade release platform, we must replace raw metadata table auto-generation with a proper database migration framework (Alembic) and run system compatibility checks during install.

### Decision
We introduced structured versioning and database migrations:
- **Alembic Database Migrations**: Configured Alembic and created an initial conditional schema migration (`fffa6e27566e_initial_schema.py`) that checks for the presence of tables and stamps the database version instead of crashing if the tables are already created (ensuring existing deployments continue working without data loss). Programmatic migration triggers run automatically on backend application lifespan startup.
- **Refactored Modular Installer**: Refactored `install.py` options and created `installer/utils.py`, `installer/validate.py`, and `installer/templates.py` modules.
- **System Pre-flight Checks**: Integrated checks in the installer for Python version, Ubuntu/Debian OS releases, and kernel networking capabilities (`sch_htb`, `ifb`, `act_mirred`).

### Consequences
- Production deployments can evolve their database schemas cleanly.
- Administrators receive early feedback if the target machine lacks required network queuing disciplines.

## [2026-07-16] Transactional Installer, Rollback & Backups Validation (Phase 2)

### Context
To ensure the installation and upgrade process does not leave system folders in a corrupted state on errors, the installer needs to back up config records beforehand, track changes, revert state on failures, and provide automated uninstallation.

### Decision
We implemented a transaction-based installation layer:
- **`RollbackManager`**: Keeps a log of written, modified, and linked assets. On errors, it restores original files from temporary `/tmp` archives and deletes newly created files in reverse order.
- **Pre-Install Validation Backups**: Integrated `installer/backup.py` which automatically archives configurations and verifies archive readability. The installer aborts immediately if backup validation fails.
- **Dry-Run & Uninstaller**: Added a `--dry-run` flag that validates options and displays content without modifying disk configurations. Added an `--uninstall` flag to stop systemd daemons, unlink configurations, and selectively purge base files.

### Consequences
- PisoWiFi can be tested safely on any host using `--dry-run` or installed without leaving system configs half-written on unexpected errors.
- Clean uninstallation allows quick platform redeployments.

## [2026-07-16] CLI framework, Doctor diagnostics & Rotating logs (Phase 3)

### Context
Administrators need a direct command-line utility to audit, diagnose, and troubleshoot the captive portal deployment, and write detailed structured logs to troubleshoot failures.

### Decision
We implemented CLI tooling and central logging:
- **`pisowifi` CLI Command**: Created a bash wrapper `bin/pisowifi` that automatically launches `installer/cli.py` using the isolated Python virtual environment, resolving module imports and dependency conflicts.
- **Diagnostics Checkups (`pisowifi doctor`)**: Developed `installer/doctor.py` implementing comprehensive, read-only system audits on interfaces, database connectivity, Uvicorn responsiveness, systemd services, kernel modules, traffic control config, and internet routing.
- **Rotating Log Manager (`installer/log_manager.py`)**: Centralized rotating log handler logging to `install.log`, `rollback.log`, `migration.log`, and `doctor.log`. Capped individual log file sizes to protect host disk capacity.

### Consequences
- The system is commercially supportable; admins can troubleshoot deployments by running `pisowifi doctor`.
- Historical logs are recorded safely in `/opt/pisowifi/logs/`.






