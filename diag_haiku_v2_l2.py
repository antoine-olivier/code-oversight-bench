"""Diagnose why Haiku Volet 2 L2 dropped TPs vs L0 (exec rc=0 vs import/setup crash vs AssertionError)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from score_bench import parse_model_json

ROOT = Path(__file__).resolve().parent
key = json.loads((ROOT / "volet2" / "key.json").read_text(encoding="utf-8"))["entries"]
l0 = {json.loads(l)["mod_id"]: json.loads(l) for l in (ROOT / "volet2" / "runs" / "claude-haiku-4-5" / "raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
l2 = {json.loads(l)["mod_id"]: json.loads(l) for l in (ROOT / "volet2" / "runs" / "claude-haiku-4-5-L2" / "raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}

dropped_reasons = Counter()
kept_reasons = Counter()
fp_filtered_reasons = Counter()

for e in key:
    mid = e["mod_id"]
    p0 = parse_model_json(l0[mid].get("raw_output", ""))
    p2 = parse_model_json(l2[mid].get("raw_output", ""))
    if not p0 or p0["verdict"] != "BUG":
        continue
    ex = l2[mid].get("exec_result", {})
    rc = ex.get("returncode")
    err = ex.get("stderr", "")
    if ex.get("timed_out"):
        bucket = "timeout"
    elif rc == 0:
        bucket = "repro_passed_rc0"
    elif "AssertionError" in err:
        bucket = "assertion_failed"
    elif "ImportError" in err or "ModuleNotFoundError" in err:
        bucket = "import_error"
    else:
        bucket = "other_exception"

    is_bug = e["label"] == "BUG"
    v2_bug = bool(p2 and p2["verdict"] == "BUG")
    if is_bug and not v2_bug:
        dropped_reasons[bucket] += 1
    elif is_bug and v2_bug:
        kept_reasons[bucket] += 1
    elif (not is_bug) and (not v2_bug):
        fp_filtered_reasons[bucket] += 1

print("BUGGY dropped by L2 (FN induced):", dict(dropped_reasons), "total=", sum(dropped_reasons.values()))
print("BUGGY kept by L2 (TP preserved): ", dict(kept_reasons), "total=", sum(kept_reasons.values()))
print("CLEAN fixed by L2 (FP removed):  ", dict(fp_filtered_reasons), "total=", sum(fp_filtered_reasons.values()))
