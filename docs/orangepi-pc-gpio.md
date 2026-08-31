# Orange Pi PC native GPIO coin hardware

## Scope and requirements

This profile supports the original **Orange Pi PC (Allwinner H3)** running **Debian 13 Trixie**. It does not apply to Orange Pi PC Plus, PC2, or another board merely because its connector looks similar. The installer reads `/proc/device-tree/model`, `/etc/os-release`, `dpkg --print-architecture`, `gpiodetect`, and `gpioinfo`. GPIO setup stops if the exact board/OS or live lines cannot be verified.

Debian 13 packages libgpiod 2.2.1 and its Python v2 binding as `gpiod` and `python3-libgpiod`; PisoWiFi uses the GPIO character devices, never deprecated `/sys/class/gpio`. See the [Debian Trixie python3-libgpiod package](https://packages.debian.org/trixie/python/python3-libgpiod) and [upstream Python `request_lines` API](https://libgpiod.readthedocs.io/en/v2.3/python_misc.html).

## Maintained pin profile

The Orange Pi-maintained [wiringOP H3 table](https://github.com/orangepi-xunlong/wiringOP#allwinner-h3) maps physical pin 29 to PA7 and physical pin 33 to PA9. The [upstream Linux H3 pinctrl driver](https://github.com/torvalds/linux/blob/master/drivers/pinctrl/sunxi/pinctrl-sun8i-h3.c) declares PA7 and PA9 as GPIO input/output lines with EINT7/EINT9 edge support.

| Purpose | Physical pin | SoC name | Legacy global number | Runtime identity |
|---|---:|---|---:|---|
| Recommended coin input | 29 | PA7 | 7 | Resolved from live `gpioinfo` |
| Recommended relay output | 33 | PA9 | 9 | Resolved from live `gpioinfo` |

The legacy number is informational only. Internally the saved canonical identity is `/dev/gpiochipN` plus its line offset, physical header pin, and SoC line name. The installer verifies that the live name matches and the line is unused. It never silently changes pins after installation. Maintained manual alternatives are physical 31/PA8, 35/PA10, and 37/PA20, subject to the same live checks.

## Mandatory safe interfaces

```text
Coin selector WHITE/GRAY
        |
        v
Optocoupler or verified 3.3V-safe pulse interface
        |
        v
Orange Pi coin-input GPIO
```

**Do not connect WHITE/GRAY directly to GPIO.** The selector’s pulse output may be open-collector, pulled up, or driven; its electrical characteristics are unknown. Measure/identify it and design the isolation input, resistor, polarity, and pull-up accordingly. Software cannot make a 5V/12V signal safe.

```text
Orange Pi relay GPIO
        |
        v
Verified 3.3V-compatible relay IN or transistor/opto driver
```

A relay board powered from 5V may still reject 3.3V logic or feed an unsafe voltage back through IN. Do not connect it until compatibility is verified. Follow the interface maker’s grounding/isolation requirements.

Power relay VCC from an appropriate 5V supply, not from a GPIO. Connect relay/driver ground only as required by the verified driver or isolation design.

The relay driver must include a correctly chosen fail-safe pull-up or pull-down so it remains OFF while the GPIO is unpowered, booting, or unclaimed after a process/kernel failure. Software initializes and drives OFF wherever it can, but cannot define an electrically floating pin while the board is off.

Power-side wiring:

```text
12V PSU + -> Relay COM
Relay NO  -> Coin Selector RED (+12V)
Coin Selector BLACK -> 12V PSU GND
```

The normally-open contact makes selector power normally OFF. The selector BLACK wire does not go to an Orange Pi GPIO. Whether grounds should be shared depends on the chosen isolated/driver interfaces.

## Installer flow

Run `sudo python3 install.py`, choose native GPIO, and confirm both external interfaces are verified for 3.3V logic. The installer then:

1. Confirms Orange Pi PC + Debian 13 Trixie without assuming the architecture.
2. Installs `gpiod` and `python3-libgpiod`.
3. Resolves PA7 and PA9 against live chip/offset/name/consumer data.
4. Allows an override only from the maintained profile and refuses used lines.
5. Asks for pulse edge and relay active LOW/HIGH; neither polarity is inferred from the module.
6. Optionally toggles the relay, always ending OFF.
7. Optionally samples each denomination three times. Only three identical, nonzero samples can be accepted; collisions and inconsistent samples are not saved.
8. Saves the exact stable selection in `/opt/pisowifi/backend/.env` and prints an exact wiring summary.

`--skip-hardware-test` records **NOT TESTED**, never success. An uncalibrated GPIO backend has an empty pulse map and ignores every pulse count until calibration.

## Runtime architecture

The existing `coin_reservations` row remains the exclusive lock. Activation now issues an opaque owner/IP-bound lease. The page heartbeats every 3 seconds and the lease expires after 12 seconds by default. These are configurable with `COIN_HEARTBEAT_SECONDS` and `COIN_SESSION_LEASE_SECONDS`.

```text
Insert Coin click -> acquire existing lock -> relay ON
page heartbeat    -> renew same lease
first GPIO edge   -> capture lease generation
pulse gap         -> group burst -> map pulse count -> pending coin
Done/close        -> relay OFF -> transactional existing credit flow
heartbeat stops   -> server expiry -> relay OFF -> finalize/release lock
```

`sendBeacon()` is only a best-effort close optimization. Server expiry is authoritative. A coin is accepted only when the listener presents the lease generation active at the burst’s first edge. Old heartbeats cannot revive an expired lease, and an old burst cannot credit a subsequent owner. Backend startup initializes the relay OFF, reconciles already-persisted pending coins through the existing accounting path, and invalidates browser leases.

Pulse processing has configurable kernel/software debounce (`COIN_DEBOUNCE_MS`), inter-pulse burst gap (`COIN_INTER_PULSE_GAP_MS`), edge polarity, and JSON pulse map (`COIN_PULSE_MAP`). Unknown counts are logged and ignored.

## Arduino fallback

Set `COIN_INTERFACE=arduino` or rerun `sudo python3 install.py --reconfigure-hardware`. The original serial discovery/reconnect loop remains in use and accepts both deployed `PULSE: 5` and legacy `PULSES: 5` packets. GPIO settings do not make Arduino installations require GPIO hardware. The no-op power controller preserves existing Arduino/external power behavior.

## Diagnostics and reconfiguration

```bash
sudo pisowifi hardware-status
sudo pisowifi hardware-test
sudo pisowifi hardware-test --calibrate
sudo pisowifi doctor
journalctl -u pisowifi-backend -u pisowifi-coin -n 100
sudo python3 install.py --reconfigure-hardware
```

`hardware-test` stops both application services so it can exclusively request the GPIO lines, initializes the relay OFF, performs the requested test, and restarts services in a `finally` path. Calibration observes pulses without creating customer credit.

Common failures:

- **Board/profile mismatch:** do not override with guessed numbers; use Arduino or add a reviewed board profile.
- **Line not found:** compare `gpioinfo` with the configured chip/offset/name; kernel/device-tree changes require explicit reconfiguration.
- **Line busy:** identify its consumer and disable the conflicting overlay/service rather than switching pins silently.
- **No pulses:** verify selector power, isolation circuit polarity/output, selected edge, and pulse gap. Never bypass isolation to test.
- **Relay inverted:** reconfigure active LOW/HIGH. Do not swap logic by rewiring unsafe voltage into GPIO.
- **No credit:** confirm a live Insert Coin lease and calibrated mapping in `hardware-status`; unknown bursts are deliberately ignored.

## Real-hardware acceptance checklist

The automated unit tests use fakes and do not assert electrical operation. On the real Orange Pi, verify the printed board/OS/architecture, live GPIO names, relay OFF at boot, relay ON only during the page lease, OFF within the configured expiry after Wi-Fi/tab loss, all denominations across multiple insertions, service restart recovery, and no GPIO voltage outside the board’s 3.3V limits.
