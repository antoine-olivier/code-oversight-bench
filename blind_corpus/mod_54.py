"""Atomic JSON checkpoint writer that preserves previous valid state on failure."""
import json
from pathlib import Path


def save_checkpoint(path: Path, payload: dict) -> None:
    """Write payload as UTF-8 JSON to path atomically.

    If JSON serialization fails (for example due to a non-serializable object), any
    existing file at path must remain untouched and intact.
    """
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
