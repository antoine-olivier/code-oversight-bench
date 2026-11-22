"""Extract JSONL records from a Colab run log between ===BEGIN_JSONL=== and ===END_JSONL===."""
from __future__ import annotations

import json
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
text = log_path.read_text(encoding="utf-8", errors="replace")
start_marker = "===BEGIN_JSONL==="
end_marker = "===END_JSONL==="
i0 = text.find(start_marker)
i1 = text.find(end_marker)
assert i0 != -1 and i1 != -1 and i1 > i0, "Markers not found in Colab log"
chunk = text[i0 + len(start_marker) : i1].strip()
lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
records = [json.loads(ln) for ln in lines]
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
print(f"EXTRACTED {len(records)} records -> {out_path}")
