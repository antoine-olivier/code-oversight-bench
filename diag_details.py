"""Diagnostic breakdown for Sonnet Volet 2 L2 and per-category tables for Volet 1 & 2."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from score_bench import parse_model_json

ROOT = Path(__file__).resolve().parent
key = json.loads((ROOT / "volet2" / "key.json").read_text(encoding="utf-8"))["entries"]
l0 = {json.loads(l)["mod_id"]: json.loads(l) for l in (ROOT / "volet2" / "runs" / "claude-sonnet-5-5" / "raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
l2 = {json.loads(l)["mod_id"]: json.loads(l) for l in (ROOT / "volet2" / "runs" / "claude-sonnet-5-5-L2" / "raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}

dropped, kept, fp_fixed, fp_kept = Counter(), Counter(), Counter(), Counter()
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
        b = "timeout"
    elif rc == 0:
        b = "repro_passed_rc0"
    elif "AssertionError" in err:
        b = "assertion_failed"
    elif "ImportError" in err or "ModuleNotFoundError" in err:
        b = "import_error"
    else:
        b = "other_exception"
    is_bug = e["label"] == "BUG"
    v2_bug = bool(p2 and p2["verdict"] == "BUG")
    if is_bug and not v2_bug:
        dropped[b] += 1
    elif is_bug and v2_bug:
        kept[b] += 1
    elif (not is_bug) and (not v2_bug):
        fp_fixed[b] += 1
    else:
        fp_kept[b] += 1

print("SONNET V2 L2:")
print("  BUGGY dropped:", dict(dropped), "total=", sum(dropped.values()))
print("  BUGGY kept:   ", dict(kept), "total=", sum(kept.values()))
print("  CLEAN fixed:  ", dict(fp_fixed), "total=", sum(fp_fixed.values()))
print("  CLEAN kept FP:", dict(fp_kept), "total=", sum(fp_kept.values()))

# Per-category summary on Volet 2 (Sonnet L0 vs Haiku L0 vs Haiku L1 vs Qwen 7B L0)
s2 = json.loads((ROOT / "volet2" / "runs" / "score-v2-7arms.json").read_text(encoding="utf-8"))
print("\nVOLET 2 PER-CATEGORY (strict_sep / n):")
cats = sorted(s2["arms"]["sonnet-v2-L0"]["per_category"].keys())
print(f"{'Category':22s} | {'n':>2s} | {'Q7B-L0':>7s} | {'Hai-L0':>7s} | {'Hai-L1':>7s} | {'Hai-L2':>7s} | {'Son-L0':>7s} | {'Son-L1':>7s}")
for c in cats:
    row = [f"{c:22s}", f"{s2['arms']['sonnet-v2-L0']['per_category'][c]['n']:2d}"]
    for arm in ("qwen7b-v2-L0", "haiku-v2-L0", "haiku-v2-L1", "haiku-v2-L2", "sonnet-v2-L0", "sonnet-v2-L1"):
        d = s2["arms"][arm]["per_category"][c]
        row.append(f"{d['strict_sep']:2d}/{d['n']:<2d}  ")
    print(" | ".join(row))
