"""Inspect Sonnet L2's 3 remaining false positives on Volet 1 (P02, P04, P22 clean)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
key = json.loads((ROOT / "key.json").read_text(encoding="utf-8"))["entries"]
clean_by_pair = {e["pair_id"]: e["mod_id"] for e in key if e["label"] == "CLEAN"}
l2 = {
    json.loads(ln)["mod_id"]: json.loads(ln)
    for ln in (ROOT / "runs" / "claude-sonnet-5-5-L2" / "raw.jsonl").read_text(encoding="utf-8").splitlines()
    if ln.strip()
}

for pid in ("P02", "P04", "P22"):
    mid = clean_by_pair[pid]
    rec = l2[mid]
    print(f"================ {pid} CLEAN ({mid}) ================")
    print("VERDICT RAW:", rec["raw_output"][:400])
    print("EXEC:", rec.get("exec_result", {}).get("returncode"), "|", rec.get("exec_result", {}).get("stderr", "")[:250])
    print("REPRO:\n", rec.get("repro_code", "")[:500])
