from datetime import datetime, timezone

def get_utc_now() -> datetime:
    """Returns naive datetime representing current UTC time for consistent DB storage and comparisons."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def parse_iso_datetime(iso_str: str) -> datetime:
    """Parses an ISO 8601 datetime string and returns a naive UTC datetime."""
    dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
