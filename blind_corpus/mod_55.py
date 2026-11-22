"""JSON Lines reader supporting files exported with or without a UTF-8 BOM."""
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    """Read non-empty JSON objects from a UTF-8 JSONL file, tolerating a leading UTF-8 BOM."""
    text = path.read_text(encoding="utf-8-sig")
    records: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(json.loads(stripped))
    return records
