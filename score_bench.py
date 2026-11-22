"""Deterministic scorer for code-bench-2026-11-22 with Wilson & paired bootstrap 95% CIs."""
from __future__ import annotations

import argparse
import json
import math
import random
import re
from pathlib import Path


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt((p * (1.0 - p) + z * z / (4 * n)) / n)
    return (max(0.0, center - half), min(1.0, center + half))


def parse_model_json(raw_text: str) -> dict | None:
    """Extract JSON verdict object from raw model text (handles markdown code fences)."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None
    text = raw_text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1)
    else:
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last > first:
            text = text[first : last + 1]
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    verdict = str(obj.get("verdict", "")).strip().upper()
    if verdict not in ("BUG", "CLEAN"):
        return None
    fn = obj.get("bug_function")
    if isinstance(fn, str):
        fn = fn.strip()
        if fn.lower() in ("", "null", "none"):
            fn = None
        else:
            fn = fn.split(".")[-1].replace("()", "").strip()
    else:
        fn = None
    return {"verdict": verdict, "bug_function": fn, "raw_parsed": obj}


def load_arm_predictions(raw_jsonl: Path) -> dict[str, dict | None]:
    preds: dict[str, dict | None] = {}
    for line in raw_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        mod_id = rec["mod_id"]
        preds[mod_id] = parse_model_json(rec.get("raw_output", ""))
    return preds


def paired_bootstrap_ci(
    pair_flags: list[int], draws: int = 2000, seed: int = 0
) -> tuple[float, float]:
    n = len(pair_flags)
    if n == 0:
        return (0.0, 0.0)
    rng = random.Random(seed)
    vals = []
    for _ in range(draws):
        s = sum(pair_flags[rng.randrange(n)] for _ in range(n))
        vals.append(s / n)
    vals.sort()
    return (vals[int(0.025 * draws)], vals[min(draws - 1, int(0.975 * draws))])


def paired_diff_bootstrap_ci(
    a_flags: list[int], b_flags: list[int], draws: int = 2000, seed: int = 0
) -> tuple[float, float]:
    assert len(a_flags) == len(b_flags)
    n = len(a_flags)
    rng = random.Random(seed)
    diffs = []
    for _ in range(draws):
        sa = 0
        sb = 0
        for _ in range(n):
            idx = rng.randrange(n)
            sa += a_flags[idx]
            sb += b_flags[idx]
        diffs.append((sa - sb) / n)
    diffs.sort()
    return (diffs[int(0.025 * draws)], diffs[min(draws - 1, int(0.975 * draws))])


def score_arm(key_entries: list[dict], preds: dict[str, dict | None]) -> dict:
    by_pair: dict[str, dict[str, dict]] = {}
    for e in key_entries:
        by_pair.setdefault(e["pair_id"], {})[e["label"]] = e

    pair_ids = sorted(by_pair.keys())
    strict_tp_flags: list[int] = []
    verdict_tp_flags: list[int] = []
    fp_flags: list[int] = []
    strict_sep_flags: list[int] = []
    verdict_sep_flags: list[int] = []
    parse_failures = 0
    missing_mods = 0
    per_cat: dict[str, dict[str, int]] = {}
    pair_details: list[dict] = []

    for pid in pair_ids:
        b_ent = by_pair[pid]["BUG"]
        c_ent = by_pair[pid]["CLEAN"]
        cat = b_ent["category"]
        cs = per_cat.setdefault(cat, {"n": 0, "strict_tp": 0, "verdict_tp": 0, "fp": 0, "strict_sep": 0})
        cs["n"] += 1

        b_pred = preds.get(b_ent["mod_id"])
        c_pred = preds.get(c_ent["mod_id"])
        if b_ent["mod_id"] not in preds:
            missing_mods += 1
        elif b_pred is None:
            parse_failures += 1
        if c_ent["mod_id"] not in preds:
            missing_mods += 1
        elif c_pred is None:
            parse_failures += 1

        b_v = b_pred["verdict"] if b_pred else "PARSE_FAIL"
        b_fn = b_pred["bug_function"] if b_pred else None
        c_v = c_pred["verdict"] if c_pred else "PARSE_FAIL"

        v_tp = 1 if b_v == "BUG" else 0
        s_tp = 1 if (b_v == "BUG" and b_fn == b_ent["target_function"]) else 0
        fp = 1 if c_v == "BUG" else 0
        v_sep = 1 if (b_v == "BUG" and c_v == "CLEAN") else 0
        s_sep = 1 if (s_tp == 1 and c_v == "CLEAN") else 0

        verdict_tp_flags.append(v_tp)
        strict_tp_flags.append(s_tp)
        fp_flags.append(fp)
        verdict_sep_flags.append(v_sep)
        strict_sep_flags.append(s_sep)

        cs["strict_tp"] += s_tp
        cs["verdict_tp"] += v_tp
        cs["fp"] += fp
        cs["strict_sep"] += s_sep

        pair_details.append(
            {
                "pair_id": pid,
                "category": cat,
                "target_function": b_ent["target_function"],
                "buggy_verdict": b_v,
                "buggy_fn": b_fn,
                "clean_verdict": c_v,
                "strict_tp": s_tp,
                "fp": fp,
                "strict_sep": s_sep,
            }
        )

    n = len(pair_ids)
    s_tp_k = sum(strict_tp_flags)
    v_tp_k = sum(verdict_tp_flags)
    fp_k = sum(fp_flags)
    s_sep_k = sum(strict_sep_flags)
    v_sep_k = sum(verdict_sep_flags)
    bal_acc = 0.5 * ((v_tp_k / n) + (1.0 - fp_k / n)) if n else 0.0

    def fmt_prop(k: int, flags: list[int]) -> dict:
        w = wilson_ci(k, n)
        b = paired_bootstrap_ci(flags)
        return {
            "k": k,
            "n": n,
            "rate": round(k / n, 4) if n else 0.0,
            "wilson_95": [round(w[0], 4), round(w[1], 4)],
            "bootstrap_95": [round(b[0], 4), round(b[1], 4)],
        }

    return {
        "n_pairs": n,
        "missing_mods": missing_mods,
        "parse_failures": parse_failures,
        "strict_tpr": fmt_prop(s_tp_k, strict_tp_flags),
        "verdict_tpr": fmt_prop(v_tp_k, verdict_tp_flags),
        "fpr": fmt_prop(fp_k, fp_flags),
        "strict_paired_separation": fmt_prop(s_sep_k, strict_sep_flags),
        "verdict_paired_separation": fmt_prop(v_sep_k, verdict_sep_flags),
        "balanced_accuracy": round(bal_acc, 4),
        "per_category": per_cat,
        "_flags": {
            "strict_tp": strict_tp_flags,
            "verdict_tp": verdict_tp_flags,
            "fp": fp_flags,
            "strict_sep": strict_sep_flags,
            "verdict_sep": verdict_sep_flags,
        },
        "pair_details": pair_details,
    }


def _selftest() -> int:
    key = [
        {"mod_id": "m1", "pair_id": "P01", "category": "c1", "label": "BUG", "target_function": "foo"},
        {"mod_id": "m2", "pair_id": "P01", "category": "c1", "label": "CLEAN", "target_function": None},
        {"mod_id": "m3", "pair_id": "P02", "category": "c1", "label": "BUG", "target_function": "bar"},
        {"mod_id": "m4", "pair_id": "P02", "category": "c1", "label": "CLEAN", "target_function": None},
    ]
    perfect = {
        "m1": parse_model_json('{"verdict": "BUG", "bug_function": "foo"}'),
        "m2": parse_model_json('{"verdict": "CLEAN", "bug_function": null}'),
        "m3": parse_model_json('```json\n{"verdict": "BUG", "bug_function": "Cls.bar()"}\n```'),
        "m4": parse_model_json('{"verdict": "CLEAN", "bug_function": null}'),
    }
    res_p = score_arm(key, perfect)
    assert res_p["strict_tpr"]["k"] == 2 and res_p["fpr"]["k"] == 0 and res_p["strict_paired_separation"]["k"] == 2

    all_bug = {
        "m1": parse_model_json('{"verdict": "BUG", "bug_function": "wrong"}'),
        "m2": parse_model_json('{"verdict": "BUG", "bug_function": "x"}'),
        "m3": parse_model_json("not json"),
        "m4": parse_model_json('{"verdict": "CLEAN", "bug_function": null}'),
    }
    res_b = score_arm(key, all_bug)
    assert res_b["strict_tpr"]["k"] == 0 and res_b["verdict_tpr"]["k"] == 1
    assert res_b["fpr"]["k"] == 1 and res_b["parse_failures"] == 1
    assert res_b["strict_paired_separation"]["k"] == 0
    print("SCORE_BENCH SELFTEST PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--key", type=Path)
    ap.add_argument("--arm", action="append", help="name=path/to/raw.jsonl")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    key_data = json.loads(args.key.read_text(encoding="utf-8"))
    entries = key_data["entries"]
    results: dict = {"arms": {}, "comparisons": {}}
    raw_flags: dict[str, dict[str, list[int]]] = {}

    for spec in args.arm or []:
        name, path_s = spec.split("=", 1)
        preds = load_arm_predictions(Path(path_s))
        scored = score_arm(entries, preds)
        raw_flags[name] = scored.pop("_flags")
        results["arms"][name] = scored

    arm_names = list(results["arms"].keys())
    for i in range(len(arm_names)):
        for j in range(i + 1, len(arm_names)):
            a, b = arm_names[i], arm_names[j]
            comp = {}
            for metric in ("strict_tp", "verdict_tp", "fp", "strict_sep", "verdict_sep"):
                lo, hi = paired_diff_bootstrap_ci(raw_flags[a][metric], raw_flags[b][metric])
                diff = (sum(raw_flags[a][metric]) - sum(raw_flags[b][metric])) / len(raw_flags[a][metric])
                comp[metric] = {
                    "diff_a_minus_b": round(diff, 4),
                    "bootstrap_95": [round(lo, 4), round(hi, 4)],
                    "established": (lo > 0.0) or (hi < 0.0),
                }
            results["comparisons"][f"{a}_vs_{b}"] = comp

    out_txt = json.dumps(results, indent=2)
    if args.out:
        args.out.write_text(out_txt, encoding="utf-8")
    else:
        print(out_txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
