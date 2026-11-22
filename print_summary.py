"""Print concise markdown summary of any score_bench.py JSON output."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print("| Arm | Strict TPR | FPR | Strict Sep | Bal Acc | ParseFail |")
    print("|---|---|---|---|---|---|")
    for name, a in data["arms"].items():
        tpr = a["strict_tpr"]
        fpr = a["fpr"]
        sep = a["strict_paired_separation"]
        print(
            f"| {name} | {tpr['k']}/{tpr['n']} ({tpr['rate']*100:.1f}%) "
            f"| {fpr['k']}/{fpr['n']} ({fpr['rate']*100:.1f}%) "
            f"| {sep['k']}/{sep['n']} ({sep['rate']*100:.1f}%) "
            f"| {a['balanced_accuracy']*100:.1f}% | {a['parse_failures']} |"
        )
    print("\nEstablished paired diffs (95% bootstrap CI excludes 0):")
    for k, d in data.get("comparisons", {}).items():
        hits = []
        for m in ("strict_tp", "fp", "strict_sep"):
            if m in d and d[m]["established"]:
                lo, hi = d[m]["bootstrap_95"]
                hits.append(f"{m}={d[m]['diff_a_minus_b']*100:+.1f}pts [{lo*100:+.1f},{hi*100:+.1f}]")
        if hits:
            print(f"- {k}: " + " ; ".join(hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
