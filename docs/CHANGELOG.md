# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [v1.0.4] - 2026-07-14

### Performance & Reliability

- **Consolidated client & session queries in GET /api/v1/session** (`session.py`): Query client and session (active or paused) using a single `LEFT OUTER JOIN` database lookup instead of 3 sequential repository queries. Saves 2 database round-trips per 5-second client status poll.
- **Removed duplicate methods in SessionRepository** (`session_repository.py`): Cleaned up unused legacy query methods `get_active_by_client` and `get_paused_by_client` to decrease maintenance friction.
- **Removed spurious DB commit on session poll** (`session.py`): Every 5-second session poll was writing `remaining_minutes` back to MySQL, generating 12 writes/minute/client. Eliminated since the value is always recomputed from `end_time`.
- **Removed module-level `print()` in firewall_service**: Was firing on every import, polluting systemd journal.
- **Removed 3 no-op scheduler jobs**: `sync_firewall`, `check_health`, and `cleanup` were empty stubs registered on 5-second/30-minute APScheduler intervals, causing unnecessary thread wakeups.
- **Replaced full ORM hydration with `COUNT(*)` for 150-session capacity check** (`coin.py`): Previously fetched all active session objects just to call `len()`.
- **Fixed N+1 query in `expire_sessions`** (`jobs.py`): Each expired session was triggering a separate Client DB query. Replaced with a single JOIN query covering both expiration checks.
- **Replaced full ORM hydration with `COUNT(*)` in health endpoint** (`health.py`): Two `get_all()` calls loading all sessions replaced with two `SELECT COUNT(*)` index scans.
- **Added `count_active_sessions()` to SessionRepository**: Lean COUNT method using the `ix_sessions_status` index.
- **Removed 40+ console.log calls from SoundManager in production**: Log calls gated by `import.meta.env.DEV` — fully preserved in development, eliminated from production builds.
- **Frontend rebuilt**: New bundle `index-nkRZ_OnN.js` (250 KB / 80.87 KB gzip).

### Nginx (manual apply required)
- **Added gzip compression**: JS bundle served compressed (~82 KB vs 249 KB). Apply with: `sudo nginx -t && sudo systemctl reload nginx`
- **Added immutable Cache-Control for hashed assets**: 1-year cache for Vite content-hashed JS/CSS.

### Systemd (manual apply required)
- **Raise `LimitNOFILE` soft limit**: Add `LimitNOFILE=65535` to `[Service]` section of `pisowifi-backend.service`. Apply with: `sudo systemctl daemon-reload && sudo systemctl restart pisowifi-backend`

## [v1.0.3] - 2026-07-14

### Fixed
- **30-Second Countdown Timer Freeze**: Resolved an issue where the coin reservation countdown froze at 30 when an active session was running. The `onClose` callback parameter was memoized in parent views, and the inner `setInterval` countdown timer inside `CoinPopup` was decoupled from the callback reference lifecycle using a mutable React `useRef` reference.

### Changed
- **Pause Audio Feedback**: Changed the Pause Session button audio feedback to play `explosion.mp3` once (non-looping, restarts if clicked repeatedly) instead of looping the `nuke-alarm.mp3`.
- **Improved Countdown Glow**: Noticeably enhanced the animated neon border glow on the countdown panel by layering multiple drop shadows (mixing primary cyan and secondary purple) and introducing a smooth, layout-safe hardware-accelerated transform pulse.

## [v1.0.2] - 2026-07-14

### Added
- **Always-Visible Insert Coin Button**: The "Insert Coin" button is now permanently visible in all states (idle, active, paused, resumed) to allow users to extend their connection at any time.
- **Premium Border Glow Animation**: Added a soft neon pulsing border glow to the countdown popup modal, pulsing in rhythm with the countdown clock using CSS animations.
- **Success Chimes**:
  - `success.mp3` plays on every successfully inserted coin.
  - `success.mp3` plays on click when resuming a paused session.
- **Pause Warning Alarm**:
  - `nuke-alarm.mp3` immediately plays and loops from the beginning when the Pause Session button is clicked.

### Changed
- **Pause/Resume Coexistence layout**: Styled Pause and Resume buttons with a dark glass-like secondary variant (`.btn-secondary`) to stack cleanly and elegantly under the primary "Insert Coin" button.

## [v1.0.1] - 2026-07-14

### Added
- **Concurrent Session Limit**: Capped new concurrent active sessions to 150 during slot activation to prevent `tc` and `nftables` from exhausting kernel memory.

### Fixed
- **Arduino Serial Disconnect Crash**: Caught `OSError` in addition to `serial.SerialException` in `SerialManager` to ensure the coin listener safely waits for reconnection instead of crashing when the USB is unplugged.

## [v1.0.0] - 2026-07-14
### Added
- **Exclusive Coin Slot Reservation**: The coin acceptor is now disabled by default. Clicking "Insert Coin" exclusively locks the hardware to the user's MAC address for 30 seconds. Other clients receive a `409 Conflict`. Lock is released on "Done" or timeout.
- **Centralized Sound System**: Added `SoundManager.js` to the React frontend.
- **Audio Assets**: `/opt/pisowifi/sfx` is now served statically by FastAPI at `/api/sfx/`.
- **Sound Events**: 
  - Plays `explosion.mp3` on "Insert Coin" activation.
  - Loops `nuke-alarm.mp3` during coin insertion countdown.
  - Plays `chicken-screaming.mp3` followed by `success.mp3` upon pressing "Done" with inserted coins.
- **Comprehensive Documentation**: Added complete architectural and API documentation inside `/opt/pisowifi/docs/`.

### Fixed
- **Pause/Resume Timer Issue**: Addressed state mismatch where time continued running on backend while paused on frontend.
- **Bandwidth Shaping (Traffic Control)**: Fixed `FileNotFoundError` caused by systemd's limited `$PATH` by utilizing absolute paths (`/usr/sbin/tc`) in `BandwidthService`.
- **TC Filter Deletion Bug**: Fixed `tc filter del` failures by ensuring `prio 1` is explicitly defined during both creation and deletion of `u32` matching rules.

### Changed
- **Bandwidth Limits**: Enforced strict 10 Mbps Download and 10 Mbps Upload per authenticated user.

### Security
- **Hardware Access**: Mitigated "coin theft" race conditions by locking hardware to a single MAC address at a time.
