"""Extract L1_RECORD and L2_RECORD JSONL lines from a Colab ablation log."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    log_path = Path(sys.argv[1])
    out_l1 = Path(sys.argv[2])
    out_l2 = Path(sys.argv[3])
    out_l1.parent.mkdir(parents=True, exist_ok=True)
    out_l2.parent.mkdir(parents=True, exist_ok=True)

    l1_rows: list[str] = []
    l2_rows: list[str] = []
    for raw_ln in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        ln = raw_ln.strip()
        if ln.startswith("L1_RECORD:"):
            obj = json.loads(ln[len("L1_RECORD:"):])
            l1_rows.append(json.dumps(obj, ensure_ascii=False))
        elif ln.startswith("L2_RECORD:"):
            obj = json.loads(ln[len("L2_RECORD:"):])
            l2_rows.append(json.dumps(obj, ensure_ascii=False))

    out_l1.write_text("\n".join(l1_rows) + ("\n" if l1_rows else ""), encoding="utf-8")
    out_l2.write_text("\n".join(l2_rows) + ("\n" if l2_rows else ""), encoding="utf-8")
    print(f"EXTRACTED L1={len(l1_rows)} -> {out_l1} | L2={len(l2_rows)} -> {out_l2}")
    return 0 if (l1_rows and l2_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
