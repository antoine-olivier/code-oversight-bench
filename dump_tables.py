"""Dump exact publication-ready tables (point estimates + Wilson/bootstrap 95% CIs) from score JSONs."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def fmt(d: dict) -> str:
    lo, hi = d["wilson_95"]
    return f"{d['k']}/{d['n']} ({d['rate']*100:.1f}%, [{lo*100:.1f}, {hi*100:.1f}])"


def dump_file(path: Path, title: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"### {title}")
    print("| Arm | Strict TPR (95% Wilson) | Verdict TPR | FPR (95% Wilson) | Strict Sep (95% Wilson) | Bal Acc | ParseFail |")
    print("|---|---|---|---|---|---|---|")
    for name, a in data["arms"].items():
        vt = a["verdict_tpr"]
        print(
            f"| {name} | {fmt(a['strict_tpr'])} | {vt['k']}/{vt['n']} ({vt['rate']*100:.1f}%) "
            f"| {fmt(a['fpr'])} | {fmt(a['strict_paired_separation'])} "
            f"| {a['balanced_accuracy']*100:.1f}% | {a['parse_failures']} |"
        )
    print()


def main() -> int:
    for arg in sys.argv[1:]:
        p = Path(arg)
        dump_file(p, p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
