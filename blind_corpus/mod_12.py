"""UTC-safe deadline comparison for ISO-8601 timestamps with offsets."""
from datetime import datetime, timezone


def parse_iso_utc(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp (accepting trailing 'Z') and convert to UTC."""
    norm = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
    dt = datetime.fromisoformat(norm)
    if dt.tzinfo is None:
        raise ValueError("Timezone offset required")
    return dt.astimezone(timezone.utc)


def is_before_deadline(event_ts: str, deadline_ts: str) -> bool:
    """Return True if event_ts occurs strictly before deadline_ts in absolute UTC time.

    Timestamps may carry different timezone offsets (for example +01:00 vs -08:00).
    """
    return parse_iso_utc(event_ts) < parse_iso_utc(deadline_ts)
