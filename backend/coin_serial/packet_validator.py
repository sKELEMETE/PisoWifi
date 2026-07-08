def validate_packet(packet: str) -> int | None:
    packet = packet.strip().upper()

    if not packet.startswith("PULSES:"):
        return None

    try:
        value = int(packet.split(":", 1)[1])
    except ValueError:
        return None

    return value if 1 <= value <= 20 else None
