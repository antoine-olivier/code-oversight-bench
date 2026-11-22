"""Run the frontier Claude arm on the 60 sealed blind modules via `claude -p --tools ""`."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BLIND_DIR = ROOT / "blind_corpus"

SYSTEM_PROMPT = (
    "You are an independent Python code reviewer. Review the standalone module below "
    "strictly against its docstring specification. Report whether the module contains a "
    "genuine functional or security bug that violates its specification (ignore style "
    "preferences, missing optional features, or docstring formatting). "
    "Reply ONLY with a single JSON object matching this exact schema:\n"
    '{"verdict": "BUG" | "CLEAN", "bug_function": "<function_name or null>", '
    '"bug_line_approx": <integer or null>, "explanation": "<1-3 concise sentences>"}'
)

REAL_CODE_SYSTEM_PROMPT = (
    "You are an independent Python code reviewer. Review the Python code below "
    "for genuine functional or security bugs (ignore style preferences, missing optional "
    "features, or formatting). Reply ONLY with a single JSON object matching this exact schema:\n"
    '{"verdict": "BUG" | "CLEAN", "bug_function": "<function_name or null>", '
    '"bug_line_approx": <integer or null>, "explanation": "<1-3 concise sentences>"}'
)


def call_claude_one(
    mod_path: Path, model: str, empty_cwd: str, timeout: int, sys_prompt: str = SYSTEM_PROMPT
) -> dict:
    code = mod_path.read_text(encoding="utf-8")
    user_msg = (
        f"Module `{mod_path.name}`:\n\n```python\n{code}\n```\n\n"
        "Return ONLY the JSON verdict object."
    )
    cmd = [
        "claude",
        "-p",
        "--setting-sources",
        "project",
        "--strict-mcp-config",
        "--model",
        model,
        "--system-prompt",
        sys_prompt,
        "--tools",
        "",
        "--output-format",
        "json",
        "--no-session-persistence",
    ]
    env = dict(os.environ)
    env["MAX_THINKING_TOKENS"] = "0"
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        input=user_msg,
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=empty_cwd,
        env=env,
        timeout=timeout,
    )
    elapsed = round(time.perf_counter() - t0, 2)
    raw_text = ""
    meta = {}
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
            raw_text = payload.get("result", "")
            meta = {
                "is_error": payload.get("is_error"),
                "duration_ms": payload.get("duration_ms"),
                "usage": payload.get("usage"),
            }
        except json.JSONDecodeError:
            raw_text = proc.stdout
    return {
        "mod_id": mod_path.stem,
        "model": model,
        "returncode": proc.returncode,
        "elapsed_sec": elapsed,
        "raw_output": raw_text,
        "stderr_head": proc.stderr[:300] if proc.stderr else "",
        "meta": meta,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blind-dir", type=Path, default=BLIND_DIR)
    ap.add_argument("--real-code", action="store_true")
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    sys_prompt = REAL_CODE_SYSTEM_PROMPT if args.real_code else SYSTEM_PROMPT
    mods = sorted(args.blind_dir.glob("mod_*.py"))
    assert len(mods) > 0, f"No blind modules found in {args.blind_dir}"
    args.out.parent.mkdir(parents=True, exist_ok=True)

    done = set()
    if args.out.exists():
        for ln in args.out.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                rec = json.loads(ln)
                if rec.get("returncode") == 0 and rec.get("raw_output"):
                    done.add(rec["mod_id"])

    todo = [p for p in mods if p.stem not in done]
    print(f"[claude-arm] model={args.model} total={len(mods)} done={len(done)} todo={len(todo)}", flush=True)
    if not todo:
        return 0

    lock = threading.Lock()
    failures = 0
    with tempfile.TemporaryDirectory() as empty_cwd:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(call_claude_one, p, args.model, empty_cwd, args.timeout, sys_prompt): p for p in todo}
            completed = len(done)
            for fut in concurrent.futures.as_completed(futs):
                rec = fut.result()
                with lock:
                    if rec.get("returncode") == 0 and rec.get("raw_output"):
                        with args.out.open("a", encoding="utf-8") as fh:
                            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        completed += 1
                    else:
                        failures += 1
                    if (completed + failures) % 20 == 0 or (completed + failures) == len(mods):
                        print(
                            f"  [{completed}/{len(mods)}] ok (failures={failures}) last={rec['mod_id']} {rec['elapsed_sec']}s",
                            flush=True,
                        )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
