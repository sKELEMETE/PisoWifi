# TODO

## Critical
- [x] Monitor real-world concurrent connections to ensure `tc` and `nftables` rules do not exhaust kernel memory.

## High
- [x] Verify Arduino Serial disconnect/reconnect behavior in `CoinService` to prevent backend crashing if the USB is unplugged.

## Medium
- [ ] Implement database backups (MariaDB/MySQL backup script or replication).
- [ ] Investigate older Android Captive Portal behavior when session is paused.

## Low
- [ ] Create an admin dashboard to visualize active sessions and total daily revenue.
- [ ] Consolidate Nginx config blocks to make future proxy updates easier.

## Future Ideas
- [ ] Multi-AP roaming support (Using a central RADIUS or migrating from MAC tracking to Voucher/Token tracking).
- [ ] Implement tiered bandwidth pricing (e.g. 5 Mbps vs 20 Mbps packages).

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
