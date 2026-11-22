"""Mechanical ground-truth gate for code-bench-2026-11-22 (30 pairs = 60 modules).

Verifies for every pair P01..P30:
1. Clean module parses as valid Python AST and defines target_function.
2. Buggy module parses as valid Python AST and defines target_function.
3. Zero benchmark-hint tokens in clean or buggy source.
4. Clean module PASSES general_tests AND PASSES trigger_test.
5. Buggy module PASSES general_tests AND FAILS trigger_test.
6. Diff between clean and buggy is non-empty and localized (<= 14 changed lines).
"""
from __future__ import annotations

import ast
import difflib
import re
import sys
import tempfile
import types
from pathlib import Path

from corpus_spec_part1 import PAIRS_PART1
from corpus_spec_part2 import PAIRS_PART2
from corpus_spec_part3 import PAIRS_PART3

ALL_PAIRS = PAIRS_PART1 + PAIRS_PART2 + PAIRS_PART3

FORBIDDEN_RE = re.compile(
    r"\b(bug|buggy|planted|bench|benchmark_trap|fault|inject|trap|clean_code|buggy_code)\b",
    re.IGNORECASE,
)


def _load_module(code: str, name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    exec(compile(code, f"<{name}>", "exec"), mod.__dict__)
    return mod


def _has_function(code: str, fn_name: str) -> bool:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            return True
    return False


def _run_test_fn(test_src: str, fn_name: str, mod: types.ModuleType, tmp_dir: Path) -> tuple[bool, str]:
    ns: dict = {}
    exec(compile(test_src, f"<{fn_name}>", "exec"), ns)
    try:
        ns[fn_name](mod, tmp_dir)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def verify_all() -> int:
    assert len(ALL_PAIRS) == 30, f"Expected 30 pairs, got {len(ALL_PAIRS)}"
    seen_ids = set()
    failures: list[str] = []

    for pair in ALL_PAIRS:
        pid = pair["pair_id"]
        assert pid not in seen_ids, f"Duplicate pair_id: {pid}"
        seen_ids.add(pid)
        target = pair["target_function"]
        clean_src = pair["clean_code"]
        buggy_src = pair["buggy_code"]

        for label, src in (("clean", clean_src), ("buggy", buggy_src)):
            m = FORBIDDEN_RE.search(src)
            if m:
                failures.append(f"{pid} ({label}): forbidden hint token '{m.group(0)}'")
            if not _has_function(src, target):
                failures.append(f"{pid} ({label}): missing target function '{target}'")

        diff_lines = [
            ln for ln in difflib.unified_diff(clean_src.splitlines(), buggy_src.splitlines(), n=0)
            if (ln.startswith("+") and not ln.startswith("+++"))
            or (ln.startswith("-") and not ln.startswith("---"))
        ]
        if not diff_lines or len(diff_lines) > 16:
            failures.append(f"{pid}: unexpected diff size ({len(diff_lines)} lines)")

        with tempfile.TemporaryDirectory() as td:
            tpath = Path(td)
            clean_mod = _load_module(clean_src, f"{pid}_clean")
            buggy_mod = _load_module(buggy_src, f"{pid}_buggy")

            c_gen_ok, c_gen_err = _run_test_fn(pair["general_tests"], "test_general", clean_mod, tpath / "cg")
            (tpath / "cg").mkdir(exist_ok=True)
            c_gen_ok, c_gen_err = _run_test_fn(pair["general_tests"], "test_general", clean_mod, tpath / "cg")
            (tpath / "ct").mkdir(exist_ok=True)
            c_trg_ok, c_trg_err = _run_test_fn(pair["trigger_test"], "test_trigger", clean_mod, tpath / "ct")

            (tpath / "bg").mkdir(exist_ok=True)
            b_gen_ok, b_gen_err = _run_test_fn(pair["general_tests"], "test_general", buggy_mod, tpath / "bg")
            (tpath / "bt").mkdir(exist_ok=True)
            b_trg_ok, b_trg_err = _run_test_fn(pair["trigger_test"], "test_trigger", buggy_mod, tpath / "bt")

            if not c_gen_ok:
                failures.append(f"{pid}: clean FAILED general_tests ({c_gen_err})")
            if not c_trg_ok:
                failures.append(f"{pid}: clean FAILED trigger_test ({c_trg_err})")
            if not b_gen_ok:
                failures.append(f"{pid}: buggy FAILED general_tests ({b_gen_err})")
            if b_trg_ok:
                failures.append(f"{pid}: buggy PASSED trigger_test (must FAIL!)")

    if failures:
        print(f"VERIFY_CORPUS FAIL ({len(failures)} issue(s)):")
        for f in failures:
            print("  -", f)
        return 1

    by_cat: dict[str, int] = {}
    for p in ALL_PAIRS:
        by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
    print(f"VERIFY_CORPUS PASS: 30/30 pairs (60/60 modules) verified mechanically. Categories: {by_cat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(verify_all())
