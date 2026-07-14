# TODO

## Critical
- [x] Monitor real-world concurrent connections to ensure `tc` and `nftables` rules do not exhaust kernel memory.

## High
- [x] Verify Arduino Serial disconnect/reconnect behavior in `CoinService` to prevent backend crashing if the USB is unplugged.

## Medium
- [ ] Implement database backups (SQLite backup script or replication).
- [ ] Investigate older Android Captive Portal behavior when session is paused.

## Low
- [ ] Create an admin dashboard to visualize active sessions and total daily revenue.
- [ ] Consolidate Nginx config blocks to make future proxy updates easier.

## Future Ideas
- [ ] Multi-AP roaming support (Using a central RADIUS or migrating from MAC tracking to Voucher/Token tracking).
- [ ] Implement tiered bandwidth pricing (e.g. 5 Mbps vs 20 Mbps packages).

## Completed (v1.0.3)
- [x] Keep Insert Coin button always visible in all session states.
- [x] Add premium border pulse glow animation to countdown screen (improved to layered neon).
- [x] Play success.mp3 on every successfully inserted coin.
- [x] Play explosion.mp3 once on Pause button click (replacing nuke-alarm.mp3).
- [x] Play success.mp3 on Resume button click.
- [x] Fix 30-second reservation countdown freeze bug during active sessions.
