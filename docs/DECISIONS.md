# Architecture & Engineering Decisions

This document records the key technical and design decisions made for the PisoWiFi captive portal system.

---

## 00. Production Certification Hardening — JWT, Voucher, Installer (2026-07-21)
*   **Context:** Final audit before production certification identified two medium-severity issues: the JWT secret could silently be set to a weak/default value, and the `delete_voucher()` API could attempt to delete already-redeemed (USED) vouchers. Additionally, the installer lacked input validation for port numbers and silently ignored service restart failures.
*   **Decision:**
    - Added `warn_if_default_jwt_secret()` at `config.py` startup with common-pattern detection and character-diversity heuristics.
    - Added `ValueError` raise in `VoucherService.delete_voucher()` when status is USED, with API-layer try/except.
    - Added try/except around `int()` conversion in `install.py` line 163-168 for port inputs.
    - Added return-code inspection for `systemctl restart` calls in `install.py` lines 278-289.
*   **Consequences:** All three vulnerabilities mitigated without changing any API surface or breaking existing tests. 38/38 tests pass.

## 0. Voucher System Production Certification & Authentication Hardening (2026-07-21)
*   **Context:** Admin login returned HTTP 401 due to bcrypt salt truncation during environment variable interpolation of `$` characters. First-time client voucher redemption returned HTTP 404 due to strict `get_by_mac()` checks.
*   **Decision:**
    - Passed `interpolate=False` to `load_dotenv()` in [config.py](file:///opt/pisowifi/backend/config.py) and single-quoted `ADMIN_PASSWORD_HASH` in `.env`.
    - Switched client lookup in `_process_voucher_redemption()` ([voucher.py](file:///opt/pisowifi/backend/api/v1/voucher.py)) to `ClientRepository.get_or_create()`.
    - Added explicit logger warnings in `verify_password()` ([auth.py](file:///opt/pisowifi/backend/utils/auth.py)) for `ValueError` hash exceptions.
*   **Consequences:** Resolved all 4 diagnostic issues. 36/36 tests pass cleanly. 100% production certified.

---

## 1. Pricing and Billing

### Decision: Accumulated Peso-Based Pricing
*   **Context:** Under the previous model, each coin dropped was processed individually, immediately crediting minutes. This made it impossible to implement progressive package-based pricing (e.g. five ₱1 coins should grant the ₱5 package rate of 3 hours rather than 5 × 20m = 100m).
*   **Decision:** Pricing is determined strictly from the **total accumulated peso amount** inserted during a single reservation slot. 
*   **Ledger Accuracy:** To maintain financial tracking, individual coins continue to write `Sale` records, but their `minutes` field is set to `0` so they do not duplicate time. The session is extended by the total package minutes in a single database transaction.

### Decision: Non-Pausable ₱20 Package (24-Hour)
*   **Context:** The operator wants to offer high-duration packages at a steep discount (₱20 for 24 hours) but prevent users from abusing the discount by pausing/unpausing the session over several weeks.
*   **Decision:** Sessions containing a ₱20 purchase are flagged with `pause_allowed = false`.
    *   **Backend:** The `POST /api/v1/session/pause/{mac}` endpoint checks this flag and rejects requests with an HTTP error.
    *   **Frontend:** The Pause button is hidden dynamically when `session.pause_allowed === false`.

### Decision: Backend-Driven Pricing Table
*   **Context:** Hardcoding rate configurations on the client side introduces duplication and risks state divergence if the database rate settings are altered by the administrator.
*   **Decision:** The backend `/pricing` endpoint serves as the single source of truth. The frontend queries this API on load to fetch available rate durations (e.g. ₱1, ₱5, ₱10, ₱15, ₱20), rendering package descriptions dynamically without client-side pricing logic or hardcoded time mappings.

---

## 2. User Experience and Audio

### Decision: Replaced "Session" with "Time" Terminology
*   **Context:** Non-technical captive portal users found the word "Session" (e.g. "Remaining Session", "Pause Session") abstract and confusing.
*   **Decision:** Replaced all user-facing instances of "Session" with "Time" (e.g., "Remaining Time", "Pause Time", "Resume Time") across all frontend portal pages, headers, navigation tabs, and instructions.

### Decision: Centralized SoundManager
*   **Context:** Complex sequential audio plays (e.g. playing an explosion, then starting a looping alarm, then playing a success sound) was scattered across components, resulting in overlapping audio channels and race conditions.
*   **Decision:** All sound effects are managed via a global, state-controlled `SoundManager` singleton.
*   **Autoplay Restrictions:** Browsers restrict audio playing before user interaction. `SoundManager` hooks into early document interaction events (`click`, `touchstart`, `keydown`) to unlock the audio context silently (`volume = 0` trick).
*   **Static Servicing:** Audio files are served directly by Nginx (`/api/sfx/`) to bypass the FastAPI app entirely, reducing backend CPU workload.

### Decision: Persistent Insert Coin Button
*   **Context:** Users had to wait for their session to expire or execute manual unpauses before they could add more money.
*   **Decision:** The "Insert Coin" button is permanently visible across all views (Active, Paused, Idle). This allows users to extend their time at any point in the lifecycle.

### Decision: State-Aware Session Restoration (No Landing Page Flash)
*   **Context:** After closing the coin reservation popup (clicking Done or timeout), the UI briefly loaded the Landing Page (insert state) for 1-4 seconds before background polling corrected it to Active/Paused.
*   **Decision:** When closing the popup, the frontend immediately reads the previous session state (or updated API payload) and transitions `portalState` directly to the correct view, eliminating landing page flashes.

### Decision: Centralized Dynamic Branding
*   **Context:** Hardcoded references to the app name, tagline, and logo were duplicated across multiple layouts, headers, and footer components.
*   **Decision:** Consolidated branding parameters in `branding.js` using `.env` variables (`VITE_APP_NAME`, `VITE_APP_LOGO`, `VITE_APP_TAGLINE`). All frontend view elements query this configuration to render identity details dynamically.

### Decision: Portal Single-Scroll Card Layout
*   **Context:** Card growth due to pricing table height pushed action buttons out of immediate view, causing header collisions on smaller devices.
*   **Decision:** Rendered the entire captive portal card as a single scrollable container under a thin custom scrollbar. Centered layout items block-wise and removed the fixed footer to maximize vertical layout space.

---

## 3. Reliability and Systems Engineering

### Decision: Explicit Traffic Control (tc) handles
*   **Context:** Operating standard `tc filter del` commands without specific handles caused the Linux kernel classifier to flush the entire priority block, clearing bandwidth shaping filters for all other connected clients.
*   **Decision:** Assign explicit unique hex handles (`800::{cid:x}`) derived from client class IDs. Both `tc filter add` and `tc filter del` target these handles exclusively to isolate shaping configurations.

### Decision: Core System Reliability Recovery Chain
*   **Context:** System restarts or database latency caused complete portal failure or client lockouts (since `nftables` flushes on boot).
*   **Decisions (R-01 to R-05):**
    *   **R-01 (Startup Recovery):** Lifespan startup hooks run recovery to wait for MariaDB, transition crashed sessions to paused (recalculating remaining duration in seconds), and rebuild firewall rules.
    *   **R-02 (Persistent Transactions):** Coin drops are logged in `/opt/pisowifi/run/` instead of volatile `/tmp/`, with automated boot-time reconciliation.
    *   **R-03 (Firewall Auditor):** A background scheduler job runs every 30s to reconcile `nftables` sets with the active sessions database.
    *   **R-04 (IP renewal):** Changing DHCP leases dynamically triggers firewall rule migrations to the client's new IP address.
    *   **R-05 (Clock Drift Engine):** NTP time jumps are detected via monotonic clock deltas, adjusting session `end_time` values accordingly.

### Decision: Ubuntu-Based Traffic Shaping
*   **Context:** Bandwidth limiting could be performed at the AP or portal server.
*   **Decision:** The Ubuntu gateway remains responsible for traffic shaping via `tc` (HTB qdiscs and `ifb` devices). This ensures uniform shaping across multiple AP hardware revisions without relying on proprietary controller APIs.

### Decision: Minimizing Stable Code Refactoring
*   **Context:** Rewriting stable backend routing or database logic introduces regressions.
*   **Decision:** Strictly prioritize backward-compatible enhancements. Implement fixes at the point of failure (e.g. recovery algorithms, filter commands) rather than rewriting central components.

---

## 4. Performance & Diagnostics

### Decision: Decoupled Diagnostics Caching & Thread-Safe Serial Caching
*   **Context:** Synchronous system audits (such as systemctl checks, WAN TCP handshakes, and dns resolution) and sequential hardware serial port scans on every request caused severe request latencies (~1000ms) and high system load.
*   **Decision:**
    *   **Health Caching (`HealthCacheService`):** Moved all diagnostic calculations out of the HTTP request thread. A background updater loop refreshes diagnostics in an isolated executor thread every 30 seconds.
    *   **Serial Caching:** Cached the detected serial device path in memory and verify its presence using `os.path.exists()` on subsequent checks (<0.1ms), avoiding redundant scans.
    *   **Consolidated Sales Aggregation:** Consolidated sales queries into a single database SQL statement utilizing conditional case-sums, reducing database query execution latency by 95% (from 100ms to 4.8ms).
    *   **Actual CPU Calculation:** Replaced load average metrics with true rolling CPU utilization using active/idle tick deltas from `/proc/stat`.
