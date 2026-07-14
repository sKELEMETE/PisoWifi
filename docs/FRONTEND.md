# Frontend Documentation

The frontend is a React application built with Vite. It serves as the Captive Portal UI.

## State Management (Stores)
- `sessionStore` (Zustand): Holds the global state of the user's `session` (time remaining, status) and `client` (MAC/IP).

## Key Hooks
- `useSession`: Polls the backend for session status or updates local timers.
- `useCoin`: Polls hardware coin acceptor status when the coin insertion popup is active.
- `usePauseSession`: API wrapper for sending PAUSE/RESUME requests.

## Components & Flow

### 1. `App.jsx`
Main entry point. Mounts the layout and initializes `SoundManager` audio preloading.

### 2. `PortalCard` / Main Router
Switches views based on the `session.status`.
- **UNKNOWN / NO SESSION**: Shows `InsertCoinView.jsx`
- **ACTIVE**: Shows `ActiveSessionView.jsx` (displays time left, Pause button).
- **PAUSED**: Shows `PausedView.jsx` (displays frozen time left, Resume button).

### 3. Coin Flow (`InsertCoinView.jsx`)
1. User clicks "Insert Coin".
2. `activateCoin(mac)` API is called.
3. If `success`, frontend opens `CoinPopup`, triggering `SoundManager.playExplosionThenAlarm()`.
4. User drops physical coins. `useCoin` polls backend and updates live `total_amount`. Timer is reset to 30s.
5. User clicks "Done" or 30s timeout expires.
6. `releaseCoin(mac)` API is called, `SoundManager.playSuccessSequence()` is played if coins were inserted. Session becomes ACTIVE.

### 4. Audio System (`SoundManager.js`)
Centralized singleton that orchestrates audio feedback.
- Handles browser autoplay unlocking by piggybacking on the first user interaction (click/touch).
- Suspends all audio on tab switch (`visibilitychange`).
- Stops previous sound instances natively to avoid overlapping cacophony.
