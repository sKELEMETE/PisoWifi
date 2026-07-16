# Architecture & Engineering Decisions

This document records the key technical and design decisions made for the PisoWiFi captive portal system.

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

---

## 2. User Experience and Audio

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

---

## 3. Reliability and Systems Engineering

### Decision: Core System Reliability Recovery Chain
*   **Context:** System restarts or database latency caused complete portal failure or client lockouts (since `nftables` flushes on boot).
*   **Decisions (R-01 to R-05):**
    *   **R-01 (Startup Recovery):** Lifespan startup hooks run recovery to wait for MariaDB, transition crashed sessions to paused, and rebuild firewall rules.
    *   **R-02 (Persistent Transactions):** Coin drops are logged in `/opt/pisowifi/run/` instead of volatile `/tmp/`, with automated boot-time reconciliation.
    *   **R-03 (Firewall Auditor):** A background scheduler job runs every 30s to reconcile `nftables` sets with the active sessions database.
    *   **R-04 (IP renewal):** Changing DHCP leases dynamically triggers firewall rule migrations to the client's new IP address.
    *   **R-05 (Clock Drift Engine):** NTP time jumps are detected via monotonic clock deltas, adjusting session `end_time` values accordingly.

### Decision: Ubuntu-Based Traffic Shaping
*   **Context:** Bandwidth limiting could be performed at the AP or portal server.
*   **Decision:** The Ubuntu gateway remains responsible for traffic shaping via `tc` (HTB qdiscs and `ifb` devices). This ensures uniform shaping across multiple AP hardware revisions without relying on proprietary controller APIs.
