"""Run Level 1 (adversarial 2-pass) and Level 2 (isolated Python exec) ablations via Claude bare CLI."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from score_bench import parse_model_json

L1_SYSTEM_PROMPT = (
    "You are an independent, skeptical Python code auditor. Another reviewer flagged a "
    "possible bug in the module below. Your job is to TRY TO FALSIFY that bug claim "
    "strictly against the code and its docstring/specification. Many flagged issues are "
    "false positives (misreading Python semantics, missing a guard already present, or "
    "inventing requirements not in the specification). "
    "Confirm BUG only if there is a concrete, undeniable input where the implementation "
    "violates its specification. Otherwise return CLEAN. "
    "Reply ONLY with a single JSON object matching this exact schema:\n"
    '{"verdict": "BUG" | "CLEAN", "bug_function": "<function_name or null>", '
    '"bug_line_approx": <integer or null>, "explanation": "<1-3 concise sentences>"}'
)

L2_REPRO_SYSTEM_PROMPT = (
    "You are a Python verification engineer. Another reviewer flagged a bug in the module "
    "below. Write a short, self-contained Python test script (<= 40 lines) that imports the "
    "module and tests the alleged bug on a concrete input.\n"
    "Rules:\n"
    "- Import the module exactly as instructed in the user prompt.\n"
    "- Assert the CORRECT behavior required by the module's specification/docstring.\n"
    "- If the module has the bug, an AssertionError MUST be raised. If the module is actually "
    "correct on that input, the script MUST exit cleanly with code 0.\n"
    "- Do NOT perform network calls, file deletion, or infinite loops.\n"
    "- Reply ONLY with a single ```python ... ``` code block containing the script."
)

L2_VERDICT_SYSTEM_PROMPT = (
    "You are an independent, evidence-driven Python code auditor. Another reviewer flagged "
    "a bug, and a concrete Python verification script was executed against the actual module. "
    "Inspect the module, the claim, the verification script, and the EXACT execution output.\n"
    "Rules:\n"
    "- Return BUG ONLY if the script correctly tested the specification AND the execution "
    "demonstrated a genuine violation of the specification by the module.\n"
    "- If the script passed (exit code 0), check carefully whether the module actually behaves "
    "correctly per its specification (likely CLEAN) or whether the script failed to exercise the bug.\n"
    "- If the script crashed due to a bug in the test script itself (NameError, wrong signature, "
    "invalid test setup), do NOT count that as proof of a module bug; judge strictly from code + spec.\n"
    "Reply ONLY with a single JSON object matching this exact schema:\n"
    '{"verdict": "BUG" | "CLEAN", "bug_function": "<function_name or null>", '
    '"bug_line_approx": <integer or null>, "explanation": "<1-3 concise sentences>"}'
)


def call_claude_bare(
    system_prompt: str,
    user_msg: str,
    model: str,
    empty_cwd: str,
    timeout: int,
) -> tuple[int, str, str, dict, float]:
    cmd = [
        "claude",
        "-p",
        "--setting-sources",
        "project",
        "--strict-mcp-config",
        "--model",
        model,
        "--system-prompt",
        system_prompt,
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
    return proc.returncode, raw_text, proc.stderr[:300] if proc.stderr else "", meta, elapsed


def extract_python_block(text: str) -> str:
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()


def run_isolated_repro(
    mod_path: Path,
    repro_code: str,
    import_name: str | None = None,
    pkg_root: Path | None = None,
    rel_target: str | None = None,
    exec_timeout: float = 3.0,
) -> dict:
    """Execute repro_code against mod_path inside a fresh isolated temp directory."""
    with tempfile.TemporaryDirectory(prefix="repro_iso_") as tmp:
        tmp_path = Path(tmp)
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "TEMP": tmp,
            "TMP": tmp,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        if pkg_root is not None and rel_target is not None:
            # Copy package tree without tests and overwrite the single target file with blind mod
            pkg_dst = tmp_path / "pkg_env"
            shutil.copytree(pkg_root, pkg_dst)
            target_file = pkg_dst / rel_target
            target_file.write_text(mod_path.read_text(encoding="utf-8"), encoding="utf-8")
            env["PYTHONPATH"] = str(pkg_dst)
        else:
            mod_name = import_name or mod_path.stem
            (tmp_path / f"{mod_name}.py").write_text(
                mod_path.read_text(encoding="utf-8"), encoding="utf-8"
            )
            env["PYTHONPATH"] = str(tmp_path)

        script_path = tmp_path / "_repro_check.py"
        script_path.write_text(repro_code, encoding="utf-8")

        t0 = time.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(
                [sys.executable, "-S", "-s", str(script_path)]
                if False
                else [sys.executable, str(script_path)],
                cwd=str(tmp_path),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=exec_timeout,
            )
            rc = proc.returncode
            stdout = proc.stdout[:2000]
            stderr = proc.stderr[:2000]
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            rc = -9
            stdout = (exc.stdout or "")[:1000] if isinstance(exc.stdout, str) else ""
            stderr = f"TIMEOUT after {exec_timeout}s"
        elapsed = round(time.perf_counter() - t0, 3)
        return {
            "returncode": rc,
            "timed_out": timed_out,
            "elapsed_sec": elapsed,
            "stdout": stdout,
            "stderr": stderr,
        }


def load_l0_map(l0_jsonl: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in l0_jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["mod_id"]] = rec
    return out


def format_claim(parsed: dict) -> str:
    obj = parsed.get("raw_parsed", {})
    return json.dumps(
        {
            "verdict": parsed.get("verdict"),
            "bug_function": parsed.get("bug_function"),
            "bug_line_approx": obj.get("bug_line_approx"),
            "explanation": obj.get("explanation", ""),
        },
        ensure_ascii=False,
        indent=2,
    )


def run_one_module(
    mod_path: Path,
    l0_rec: dict,
    level: str,
    model: str,
    empty_cwd: str,
    timeout: int,
    import_meta: dict | None = None,
) -> dict:
    mod_id = mod_path.stem
    l0_parsed = parse_model_json(l0_rec.get("raw_output", ""))

    # Pre-registered gate: L0 CLEAN or parse failure passes through unchanged as CLEAN
    if l0_parsed is None or l0_parsed["verdict"] != "BUG":
        passthrough = json.dumps(
            {
                "verdict": "CLEAN",
                "bug_function": None,
                "bug_line_approx": None,
                "explanation": "L0 predicted CLEAN (or unparseable); passed through by pre-registered gate.",
            }
        )
        return {
            "mod_id": mod_id,
            "model": model,
            "level": level,
            "skipped_clean_in_l0": True,
            "returncode": 0,
            "elapsed_sec": 0.0,
            "raw_output": passthrough,
            "stderr_head": "",
            "meta": {},
        }

    code = mod_path.read_text(encoding="utf-8")
    claim_str = format_claim(l0_parsed)

    if level == "l1":
        user_msg = (
            f"Module `{mod_path.name}`:\n\n```python\n{code}\n```\n\n"
            f"Initial reviewer's bug claim:\n```json\n{claim_str}\n```\n\n"
            "Try to falsify this claim against the actual code and specification. "
            "Return ONLY the JSON verdict object."
        )
        rc, raw_text, stderr_head, meta, elapsed = call_claude_bare(
            L1_SYSTEM_PROMPT, user_msg, model, empty_cwd, timeout
        )
        return {
            "mod_id": mod_id,
            "model": model,
            "level": "l1",
            "skipped_clean_in_l0": False,
            "returncode": rc,
            "elapsed_sec": elapsed,
            "raw_output": raw_text,
            "stderr_head": stderr_head,
            "meta": meta,
        }

    # Level 2: Repro synthesis -> Isolated Python execution -> Evidence-grounded verdict
    if import_meta:
        import_hint = f"Import the target using `import {import_meta['import_name']}` (the package is on PYTHONPATH)."
        pkg_root = Path(import_meta["pkg_root"])
        rel_target = import_meta["rel_target"]
        import_name = import_meta["import_name"]
    else:
        import_hint = f"Import the module using `import {mod_id}` (the file `{mod_id}.py` is on PYTHONPATH)."
        pkg_root = None
        rel_target = None
        import_name = mod_id

    repro_prompt = (
        f"Module `{mod_path.name}`:\n\n```python\n{code}\n```\n\n"
        f"Initial reviewer's bug claim:\n```json\n{claim_str}\n```\n\n"
        f"{import_hint}\n"
        "Write a concise verification script (<= 40 lines) that asserts the specification "
        "behavior on the claimed failing input. Return ONLY one ```python ... ``` block."
    )
    rc1, raw_repro, err1, meta1, t1 = call_claude_bare(
        L2_REPRO_SYSTEM_PROMPT, repro_prompt, model, empty_cwd, timeout
    )
    repro_code = extract_python_block(raw_repro) if rc1 == 0 else ""
    if repro_code:
        exec_res = run_isolated_repro(
            mod_path=mod_path,
            repro_code=repro_code,
            import_name=import_name,
            pkg_root=pkg_root,
            rel_target=rel_target,
            exec_timeout=3.0,
        )
    else:
        exec_res = {
            "returncode": -1,
            "timed_out": False,
            "elapsed_sec": 0.0,
            "stdout": "",
            "stderr": f"Repro generation failed (rc={rc1}): {err1}",
        }

    verdict_prompt = (
        f"Module `{mod_path.name}`:\n\n```python\n{code}\n```\n\n"
        f"Initial reviewer's bug claim:\n```json\n{claim_str}\n```\n\n"
        f"Executed Python verification script:\n```python\n{repro_code}\n```\n\n"
        f"Observed execution result:\n```json\n{json.dumps(exec_res, ensure_ascii=False, indent=2)}\n```\n\n"
        "Based on the code, specification, script, and observed execution output, "
        "return ONLY the final JSON verdict object."
    )
    rc2, raw_verdict, err2, meta2, t2 = call_claude_bare(
        L2_VERDICT_SYSTEM_PROMPT, verdict_prompt, model, empty_cwd, timeout
    )
    return {
        "mod_id": mod_id,
        "model": model,
        "level": "l2",
        "skipped_clean_in_l0": False,
        "returncode": rc2,
        "elapsed_sec": round(t1 + t2 + exec_res["elapsed_sec"], 2),
        "raw_output": raw_verdict,
        "stderr_head": err2,
        "repro_code": repro_code,
        "exec_result": exec_res,
        "meta": {"repro": meta1, "verdict": meta2},
    }


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "mod_test.py"
        p.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        # 1. Buggy assertion should fail with AssertionError (rc != 0)
        r1 = run_isolated_repro(p, "import mod_test\nassert mod_test.add(2, 3) == 5\n")
        assert r1["returncode"] != 0 and "AssertionError" in r1["stderr"], r1
        # 2. Clean behavior should exit 0
        p2 = Path(td) / "mod_clean.py"
        p2.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        r2 = run_isolated_repro(p2, "import mod_clean\nassert mod_clean.add(2, 3) == 5\n")
        assert r2["returncode"] == 0, r2
        # 3. Timeout should be caught cleanly
        r3 = run_isolated_repro(p2, "import time\ntime.sleep(5)\n", exec_timeout=0.3)
        assert r3["timed_out"] is True and r3["returncode"] == -9, r3
    print("RUN_ABLATION_CLAUDE SELFTEST PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--blind-dir", type=Path)
    ap.add_argument("--l0", type=Path)
    ap.add_argument("--level", choices=["l1", "l2"])
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--import-map", type=Path, default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    assert args.blind_dir and args.l0 and args.level and args.out
    mods = sorted(args.blind_dir.glob("mod_*.py"))
    l0_map = load_l0_map(args.l0)
    import_map = (
        json.loads(args.import_map.read_text(encoding="utf-8"))
        if args.import_map and args.import_map.exists()
        else {}
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)

    done = set()
    if args.out.exists():
        for ln in args.out.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                rec = json.loads(ln)
                if rec.get("returncode") == 0 and rec.get("raw_output"):
                    done.add(rec["mod_id"])

    todo = [p for p in mods if p.stem not in done]
    flagged_todo = sum(
        1
        for p in todo
        if (parse_model_json(l0_map[p.stem].get("raw_output", "")) or {}).get("verdict") == "BUG"
    )
    print(
        f"[ablation-{args.level}] model={args.model} total={len(mods)} done={len(done)} "
        f"todo={len(todo)} (flagged_in_l0={flagged_todo})",
        flush=True,
    )
    if not todo:
        return 0

    lock = threading.Lock()
    with tempfile.TemporaryDirectory() as empty_cwd:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {
                ex.submit(
                    run_one_module,
                    p,
                    l0_map[p.stem],
                    args.level,
                    args.model,
                    empty_cwd,
                    args.timeout,
                    import_map.get(p.stem),
                ): p
                for p in todo
            }
            completed = len(done)
            failures = 0
            for fut in concurrent.futures.as_completed(futs):
                rec = fut.result()
                with lock:
                    if rec.get("returncode") == 0 and rec.get("raw_output"):
                        with args.out.open("a", encoding="utf-8") as fh:
                            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        completed += 1
                    else:
                        failures += 1
                    if (completed + failures) % 10 == 0 or (completed + failures) == len(mods):
                        print(
                            f"[ablation-{args.level}] {completed}/{len(mods)} ok (failures={failures})",
                            flush=True,
                        )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
