# TODO

## Critical
- [x] Monitor real-world concurrent connections to ensure `tc` and `nftables` rules do not exhaust kernel memory.

## High
- [x] Verify Arduino Serial disconnect/reconnect behavior in `CoinService` to prevent backend crashing if the USB is unplugged.

## Medium
- [ ] Implement database backups (MariaDB/MySQL backup script or replication).
- [ ] Investigate older Android Captive Portal behavior when session is paused.

## Low
- [x] Create an admin dashboard to visualize active sessions and total daily revenue.
- [ ] Consolidate Nginx config blocks to make future proxy updates easier.

## Future Ideas
- [ ] Multi-AP roaming support (Using a central RADIUS or migrating from MAC tracking to Voucher/Token tracking).
- [ ] Implement tiered bandwidth pricing (e.g. 5 Mbps vs 20 Mbps packages).

## Completed (v1.0.9 / v1.14.0)
- [x] Add weak JWT secret detection warning at startup (config.py).
- [x] Add service-layer USED status guard to VoucherService.delete_voucher().
- [x] Add int() conversion guard and service restart return-code checking to install.py.
- [x] Run final production audit across all modules (30+ files inspected). Full report saved to /tmp/pisowifi_output/remediation_report.txt.

## Completed (v1.0.8 / v1.13.0)
- [x] Fix Admin Authentication failure by enabling `interpolate=False` in `load_dotenv()` ([config.py](file:///opt/pisowifi/backend/config.py)) and single-quoting `ADMIN_PASSWORD_HASH` in `.env`.
- [x] Fix first-time client voucher redemption HTTP 404 error by utilizing `ClientRepository.get_or_create()` in `_process_voucher_redemption()` ([voucher.py](file:///opt/pisowifi/backend/api/v1/voucher.py)).
- [x] Add explicit error logging in `verify_password()` ([auth.py](file:///opt/pisowifi/backend/utils/auth.py)) for malformed bcrypt salt exceptions.
- [x] Build automated regression test suite in `test_voucher_hotfix.py` covering full voucher management lifecycle and redemption flows (36/36 tests passing).

## Completed (v1.0.7)
- [x] Optimize admin dashboard response time from ~1000ms to under 5ms using dynamic diagnostics caching (`HealthCacheService`).
- [x] Implement thread-safe serial port caching in candidate discovery, eliminating sequential port scan timeouts.
- [x] Consolidate sales query database aggregations (today, week, month) into a single SQL statement utilizing conditional aggregation.
- [x] Implement rolling CPU utilization using active/idle tick deltas from `/proc/stat`.
- [x] Configure admin dashboard polling interval to 15 seconds (reduced from 5s) to minimize DB/network overhead.
- [x] Change the DNS health label to "DNS Online" inside the frontend dashboard.

## Completed (v1.0.6)
- [x] Resolve bandwidth shaping filter bypass by introducing explicit `tc` filter handles (`800::{cid:x}`).
- [x] Fix NameError crash in jobs.py by defining missing `logger` object.
- [x] Correct remaining time unit conversion bug during system startup power recovery.
- [x] Replace all client-facing instances of "Session" terminology with "Time" across the portal.
- [x] Add dynamic branding configuration mapping for App Name, Logo, and Tagline.
- [x] Add horizontal Internet status indication beside WiFi connection status.
- [x] Redesign layout to use a single scrollable portal card wrapper and remove the footer.
- [x] Display dynamic pricing table using backend rates with "Not Pausable" visual badge on ₱20 row.

## Completed (v1.0.5)
- [x] Implement pricing table based on total accumulated peso amount.
- [x] Implement non-pausable 24-hour package for ₱20 total inserted amount.
- [x] Reject Pause requests on the backend and hide the Pause button on the frontend for non-pausable sessions.
- [x] Eliminate the Landing Page flash / UI flicker when closing the CoinPopup after extending a session.
- [x] Fix the NameError regression on Pause/Resume routes by restoring missing repository imports.
- [x] Seeding/initializing new pricing rates dynamically on system startup.

## Completed (v1.0.4)
- [x] Run `StartupSequence` recovery chain inside lifespan startup hook (`R-01`).
- [x] Move coin drop logging from volatile `/tmp/` to persistent `/opt/pisowifi/run/` (`R-02`).
- [x] Add declarative `sync_firewall` auditor job to keep `nftables` in absolute sync with database (`R-03`).
- [x] Automate IP renewal firewall migration check on client detection endpoints (`R-04`).
- [x] Add monotonic clock jump monitor in background scheduler to compensate NTP time adjustments (`R-05`).
- [x] Consolidate Client and Session SQL queries into a single outer join query (`H-01`).

## Completed (v1.0.3)
- [x] Keep Insert Coin button always visible in all session states.
- [x] Add premium border pulse glow animation to countdown screen (improved to layered neon).
- [x] Play success.mp3 on every successfully inserted coin.
- [x] Play explosion.mp3 once on Pause button click (replacing nuke-alarm.mp3).
- [x] Play success.mp3 on Resume button click.
- [x] Fix 30-second reservation countdown freeze bug during active sessions.
