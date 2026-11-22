"""UTC-safe deadline comparison for ISO-8601 timestamps with offsets."""


def normalize_ts(ts: str) -> str:
    """Normalize trailing 'Z' to '+00:00'."""
    return ts[:-1] + "+00:00" if ts.endswith("Z") else ts


def is_before_deadline(event_ts: str, deadline_ts: str) -> bool:
    """Return True if event_ts occurs strictly before deadline_ts in absolute UTC time.

    Timestamps may carry different timezone offsets (for example +01:00 vs -08:00).
    """
    return normalize_ts(event_ts) < normalize_ts(deadline_ts)
