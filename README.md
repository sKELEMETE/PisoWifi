# PisoWiFi

PisoWiFi is a FastAPI/React captive-portal gateway with nftables access control, `tc` bandwidth shaping, persistent sessions, vouchers, and two supported coin backends:

- Arduino Uno over USB serial (`COIN_INTERFACE=arduino`, the backward-compatible default)
- Orange Pi PC native GPIO through libgpiod (`COIN_INTERFACE=gpio`)

## Fresh installation

The native GPIO profile is intentionally limited to an Orange Pi PC that the installer can identify as Debian 13 Trixie. Other boards can continue using Arduino mode, but GPIO auto-configuration stops rather than guessing a pin map.

```bash
sudo apt update
sudo apt install -y git
git clone <your-pisowifi-repository>
cd pisowifi
sudo python3 install.py
```

The interactive installer installs Debian and Python dependencies, builds the frontend, configures the captive LAN and existing nginx/dnsmasq/nftables/systemd stack, applies database migrations on backend startup, and configures the selected coin interface. It preserves an existing `.env`; use `--reconfigure-hardware` to change its backend or pins.

During setup, select either the existing Arduino USB backend or native GPIO. GPIO setup proceeds only when the machine is positively detected as an Orange Pi PC running Debian 13 Trixie. It verifies the live libgpiod line names and availability before saving the selected coin-input and relay pins, asks for the electrical-interface and relay polarity settings, and offers optional relay testing and coin calibration. Do not connect the coin selector or relay control until the installer prints the final pin-specific wiring summary.

After installation, verify the services and saved hardware configuration:

```bash
sudo pisowifi doctor
sudo pisowifi hardware-status
sudo systemctl status pisowifi-backend pisowifi-coin --no-pager
```

To rerun only the interactive hardware selection later:

```bash
sudo python3 install.py --reconfigure-hardware
```

Useful safe modes:

```bash
python3 install.py --dry-run --non-interactive --coin-interface arduino
sudo python3 install.py --reconfigure-hardware
sudo python3 install.py --skip-hardware-test
sudo pisowifi doctor
sudo pisowifi hardware-status
sudo pisowifi hardware-test
sudo pisowifi hardware-test --calibrate
```

## Electrical safety

> **Never connect the 12V coin selector WHITE/GRAY signal directly to an Orange Pi GPIO.** Orange Pi PC GPIO is 3.3V logic. Use an optocoupler or another interface whose GPIO side is verified 3.3V-safe. The signal’s electrical characteristics cannot be determined by software.

A 5V relay module is not automatically 3.3V-input compatible. Verify its IN specification or use a suitable transistor/driver/opto-isolated interface. The relay switches selector power with `12V PSU + → COM`, `NO → selector RED`, and `selector BLACK → 12V PSU GND`; the relay is initialized OFF.

See [Orange Pi PC GPIO and coin hardware](docs/orangepi-pc-gpio.md) for pin selection, lease behavior, calibration, wiring, troubleshooting, and Arduino fallback.

## Development checks

```bash
cd backend
venv/bin/python -m pytest -q tests/test_coin_hardware.py tests/test_installer_hardware.py
cd ../frontend
npm ci
npm run build
```
