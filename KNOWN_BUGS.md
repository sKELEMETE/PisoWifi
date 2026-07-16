# Known Bugs & Limitations

This document tracks known bugs, limitations, and workarounds within the PisoWiFi platform.

## Network & Subnet Limitations
- **Subnet Collision on larger subnets**: The bandwidth class ID generation algorithm (`_ip_to_class_id` in [bandwidth_service.py](file:///opt/pisowifi/backend/services/bandwidth_service.py)) assumes a `/24` subnet and uses the last octet of the client's IP. Subnets larger than `/24` (e.g., `/22` or `/16`) will cause duplicate class IDs, overriding other clients' packet rules.
  - *Mitigation*: Run PisoWiFi only on `/24` subnets until Phase 3/6 dynamic mappings are introduced.

## Hardware & Connection Limitations
- **USB-only Arduino Serial Detection Heuristic**: The Arduino detection search in [device_detector.py](file:///opt/pisowifi/backend/coin_serial/device_detector.py) only looks for serial devices containing `"USB"` in their description. This misses direct UART configurations via hardware GPIO pins (`/dev/ttyS0` or `/dev/ttyAMA0`) common on Raspberry Pi and Orange Pi boards.
  - *Mitigation*: Manually set `SERIAL_PORT` in the environment if connecting via direct GPIO pins.

## Unix-Only Library Dependency
- **Fcntl reliance (RESOLVED)**: Wrapped all imports and file-lock operations for `fcntl` in check blocks, making the codebase 100% executable on Windows/macOS.

