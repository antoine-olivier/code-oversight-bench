"""Atomic JSON checkpoint writer that preserves previous valid state on failure."""
import json
import os
from pathlib import Path


def save_checkpoint(path: Path, payload: dict) -> None:
    """Write payload as UTF-8 JSON to path atomically.

    If JSON serialization fails (for example due to a non-serializable object), any
    existing file at path must remain untouched and intact.
    """
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(serialized, encoding="utf-8")
    os.replace(tmp_path, path)
