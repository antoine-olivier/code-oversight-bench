"""Inspect remaining FPs and FNs across Volet 1 L0/L1/L2 arms."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
score = json.loads((ROOT / "runs" / "score-volet1-9arms.json").read_text(encoding="utf-8"))

for arm in ("haiku-L0", "haiku-L1", "haiku-L2", "sonnet-L0", "sonnet-L2", "qwen7b-L0", "qwen7b-L2"):
    d = score["arms"][arm]
    fps = [p["pair_id"] + "(" + p["category"] + ":" + p["target_function"] + ")" for p in d["pair_details"] if p["fp"]]
    fns = [p["pair_id"] + "(" + p["category"] + ":" + p["target_function"] + ")" for p in d["pair_details"] if not p["strict_tp"]]
    print(f"=== {arm} === FP={len(fps)} FN={len(fns)}")
    print("  FPs:", ", ".join(fps[:10]) + (" ..." if len(fps) > 10 else ""))
    print("  FNs:", ", ".join(fns[:10]) + (" ..." if len(fns) > 10 else ""))
