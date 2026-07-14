# Known Bugs

## Medium Bugs
- **Old Android Device Captive Portal Quirks**
  - **Root Cause**: Devices running Android 10 or lower often aggressively close the captive portal browser or refuse to keep the page open if internet is fully blocked (PAUSED state) but DHCP remains.
  - **Temporary Workaround**: The system relies on MAC persistence. If the page closes, the backend still accurately halts the time. The user can reopen the browser to `10.0.0.1` to hit the portal and Resume.
  - **Permanent Fix Recommendation**: Implement a "Walled Garden" DNS spoof exception or explore if `nftables` can return specific ICMP replies that trick Android into keeping the portal open even while paused.

## Minor Bugs
- **Sound Autoplay Blocks**
  - **Root Cause**: Browsers heavily restrict audio autoplay.
  - **Temporary Workaround**: `SoundManager.js` binds to the first `click` or `touchstart` to unlock the audio context silently (`volume = 0` trick).
  - **Permanent Fix Recommendation**: Since the flow requires the user to click "Insert Coin" anyway, this bug is mostly mitigated by design. Ensure no sound is ever programmed to play purely on page load without interaction.
