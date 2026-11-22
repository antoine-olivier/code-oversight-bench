"""Blind, shuffle, and cryptographically seal code-bench-2026-11-22 before any model run."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from verify_corpus import ALL_PAIRS, verify_all

ROOT = Path(__file__).resolve().parent
BLIND_DIR = ROOT / "blind_corpus"
KEY_PATH = ROOT / "key.json"
MANIFEST_PATH = ROOT / "MANIFEST_SEAL.sha256"
SEED = 20261122


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if verify_all() != 0:
        print("Refusing to seal: verify_corpus failed.")
        return 1

    items = []
    for pair in ALL_PAIRS:
        items.append(
            {
                "pair_id": pair["pair_id"],
                "category": pair["category"],
                "title": pair["title"],
                "label": "CLEAN",
                "target_function": None,
                "code": pair["clean_code"],
            }
        )
        items.append(
            {
                "pair_id": pair["pair_id"],
                "category": pair["category"],
                "title": pair["title"],
                "label": "BUG",
                "target_function": pair["target_function"],
                "code": pair["buggy_code"],
            }
        )

    rng = random.Random(SEED)
    rng.shuffle(items)

    BLIND_DIR.mkdir(parents=True, exist_ok=True)
    for old in BLIND_DIR.glob("mod_*.py"):
        old.unlink()

    key_entries = []
    for idx, item in enumerate(items, start=1):
        mod_id = f"mod_{idx:02d}"
        mod_path = BLIND_DIR / f"{mod_id}.py"
        raw = item["code"].encode("utf-8")
        mod_path.write_bytes(raw)
        key_entries.append(
            {
                "mod_id": mod_id,
                "pair_id": item["pair_id"],
                "category": item["category"],
                "title": item["title"],
                "label": item["label"],
                "target_function": item["target_function"],
                "sha256": sha256_bytes(raw),
            }
        )

    KEY_PATH.write_text(json.dumps({"seed": SEED, "entries": key_entries}, indent=2), encoding="utf-8")

    manifest_files = [
        ROOT / "PROTOCOLE.md",
        ROOT / "verify_corpus.py",
        ROOT / "seal_bench.py",
        ROOT / "score_bench.py",
        KEY_PATH,
        *sorted(BLIND_DIR.glob("mod_*.py")),
    ]
    lines = []
    for p in manifest_files:
        if p.exists():
            rel = p.relative_to(ROOT).as_posix()
            lines.append(f"{sha256_bytes(p.read_bytes())}  {rel}")
    MANIFEST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SEAL_OK: {len(key_entries)} blind modules written, {len(lines)} hashes sealed in {MANIFEST_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
