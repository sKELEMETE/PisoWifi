# Known Bugs & Limitations

This document tracks known bugs, limitations, and workarounds within the PisoWiFi platform.

## Network & Subnet Limitations
- **Subnet Collision on larger subnets**: The bandwidth class ID generation algorithm (`_ip_to_class_id` in [bandwidth_service.py](file:///opt/pisowifi/backend/services/bandwidth_service.py)) assumes a `/24` subnet and uses the last octet of the client's IP. Subnets larger than `/24` (e.g., `/22` or `/16`) will cause duplicate class IDs, overriding other clients' packet rules.
  - *Mitigation*: Run PisoWiFi only on `/24` subnets until Phase 3/6 dynamic mappings are introduced.

## Hardware & Connection Limitations
- **USB-only Arduino Serial Detection Heuristic (RESOLVED)**: Overhauled `device_detector.py` to search for USB, ACM, and common hardware SBC UART ports (/dev/ttyS0, /dev/ttyAMA0, etc.) dynamically.

## Unix-Only Library Dependency
- **Fcntl reliance (RESOLVED)**: Wrapped all imports and file-lock operations for `fcntl` in check blocks, making the codebase 100% executable on Windows/macOS.

