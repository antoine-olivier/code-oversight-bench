"""Deterministic AST mutator + upstream pytest oracle + blind sealer for Volet 2 (n=100 pairs)."""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "upstream"
BLIND_DIR = ROOT / "blind_corpus"
PKG_STASH = ROOT / "pkg_snapshots"

OP_MAP: dict[str, tuple[str, str]] = {
    # (replacement_token, category)
    "<": ("<=", "order_boundary"),
    "<=": ("<", "order_boundary"),
    ">": (">=", "order_boundary"),
    ">=": (">", "order_boundary"),
    "==": ("!=", "equality_flip"),
    "!=": ("==", "equality_flip"),
    "and": ("or", "boolean_logic"),
    "or": ("and", "boolean_logic"),
    "+": ("-", "arithmetic_sign"),
    "-": ("+", "arithmetic_sign"),
}

SKIP_FILENAMES = {
    "__init__.py",
    "__main__.py",
    "__about__.py",
    "_version.py",
    "version.py",
    "conftest.py",
    "setup.py",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def is_string_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return True
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp):
        return is_string_expr(node.left) or is_string_expr(node.right)
    return False


def find_enclosing_function(tree: ast.AST, target_lineno: int) -> tuple[str | None, bool]:
    best: tuple[int, str, bool] | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            if start <= target_lineno <= end:
                span = end - start
                has_doc = bool(ast.get_docstring(node))
                if best is None or span < best[0]:
                    best = (span, node.name, has_doc)
    if best is None:
        return None, False
    return best[1], best[2]


def extract_candidates(src: str, rng: random.Random) -> list[dict]:
    """Extract clean single-line surgical AST mutation candidates preserving exact formatting."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []

    lines = src.splitlines(keepends=True)
    # Build map of (lineno, op_kind) verified by AST so we only mutate real executable ops
    ast_targets: dict[int, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            ln = node.lineno
            if isinstance(op, ast.Lt):
                ast_targets.setdefault(ln, set()).add("<")
            elif isinstance(op, ast.LtE):
                ast_targets.setdefault(ln, set()).add("<=")
            elif isinstance(op, ast.Gt):
                ast_targets.setdefault(ln, set()).add(">")
            elif isinstance(op, ast.GtE):
                ast_targets.setdefault(ln, set()).add(">=")
            elif isinstance(op, ast.Eq):
                ast_targets.setdefault(ln, set()).add("==")
            elif isinstance(op, ast.NotEq):
                ast_targets.setdefault(ln, set()).add("!=")
            elif isinstance(op, ast.Is):
                ast_targets.setdefault(ln, set()).add("is")
            elif isinstance(op, ast.IsNot):
                ast_targets.setdefault(ln, set()).add("is not")
            elif isinstance(op, ast.In):
                ast_targets.setdefault(ln, set()).add("in")
            elif isinstance(op, ast.NotIn):
                ast_targets.setdefault(ln, set()).add("not in")
        elif isinstance(node, ast.BoolOp):
            ln = node.lineno
            if isinstance(node.op, ast.And):
                ast_targets.setdefault(ln, set()).add("and")
            elif isinstance(node.op, ast.Or):
                ast_targets.setdefault(ln, set()).add("or")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            if not is_string_expr(node.left) and not is_string_expr(node.right):
                ln = node.lineno
                ast_targets.setdefault(ln, set()).add("+" if isinstance(node.op, ast.Add) else "-")

    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except tokenize.TokenError:
        return []

    candidates: list[dict] = []
    seen_line_cat: set[tuple[int, str]] = set()
    for idx, tok in enumerate(toks):
        ln = tok.start[0]
        if ln not in ast_targets:
            continue
        fn_name, has_doc = find_enclosing_function(tree, ln)
        if not fn_name or fn_name.startswith("__"):
            continue
        allowed = ast_targets[ln]
        s = tok.string
        line_text = lines[ln - 1]
        col0 = tok.start[1]
        col1 = tok.end[1]

        mut_line = None
        cat = None
        desc = None

        # Multi-word ops: "is not", "not in"
        if s == "is" and idx + 1 < len(toks) and toks[idx + 1].string == "not" and toks[idx + 1].start[0] == ln and "is not" in allowed:
            end_c = toks[idx + 1].end[1]
            mut_line = line_text[:col0] + "is" + line_text[end_c:]
            cat = "identity_membership"
            desc = "is not -> is"
        elif s == "is" and (idx + 1 >= len(toks) or toks[idx + 1].string != "not") and "is" in allowed:
            mut_line = line_text[:col0] + "is not" + line_text[col1:]
            cat = "identity_membership"
            desc = "is -> is not"
        elif s == "not" and idx + 1 < len(toks) and toks[idx + 1].string == "in" and toks[idx + 1].start[0] == ln and "not in" in allowed:
            end_c = toks[idx + 1].end[1]
            mut_line = line_text[:col0] + "in" + line_text[end_c:]
            cat = "identity_membership"
            desc = "not in -> in"
        elif s == "in" and (idx == 0 or toks[idx - 1].string != "not") and "in" in allowed:
            # Avoid `for x in y:` loops
            prev_line_prefix = line_text[:col0].lstrip()
            if not prev_line_prefix.startswith(("for ", "async for ")):
                mut_line = line_text[:col0] + "not in" + line_text[col1:]
                cat = "identity_membership"
                desc = "in -> not in"
        elif s in OP_MAP and s in allowed:
            repl, cat = OP_MAP[s]
            mut_line = line_text[:col0] + repl + line_text[col1:]
            desc = f"{s} -> {repl}"

        if mut_line is None or cat is None or mut_line == line_text:
            continue
        if (ln, cat) in seen_line_cat:
            continue
        new_lines = list(lines)
        new_lines[ln - 1] = mut_line
        mutated_src = "".join(new_lines)
        try:
            ast.parse(mutated_src)
        except SyntaxError:
            continue
        seen_line_cat.add((ln, cat))
        candidates.append(
            {
                "lineno": ln,
                "function": fn_name,
                "has_docstring": has_doc,
                "category": cat,
                "mutation": desc,
                "mutated_src": mutated_src,
                "diff": "".join(
                    difflib.unified_diff(
                        [line_text], [mut_line], fromfile="clean", tofile="buggy", n=0
                    )
                ).strip(),
            }
        )

    # Prioritize documented functions and spread across categories
    rng.shuffle(candidates)
    candidates.sort(key=lambda c: (0 if c["has_docstring"] else 1))
    return candidates


def pick_test_files(test_dir: Path, mod_stem: str) -> list[Path]:
    all_tests = sorted(test_dir.rglob("test_*.py"))
    if not all_tests:
        all_tests = sorted(test_dir.rglob("*_test.py"))
    exact = [p for p in all_tests if mod_stem.lstrip("_") in p.stem.lower()]
    if exact:
        return exact[:3]
    # Fallback: grep test files that mention mod_stem
    hits = []
    needle = mod_stem.lstrip("_")
    if len(needle) >= 3:
        for p in all_tests:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            if needle in txt:
                hits.append(p)
                if len(hits) >= 2:
                    break
    return hits


def run_pytest(
    cwd: Path,
    src_dirs: list[Path],
    test_files: list[Path],
    timeout: float = 10.0,
    noconftest: bool = False,
) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(str(d) for d in src_dirs)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = [sys.executable, "-m", "pytest", "-x", "--tb=no", "-q", "-o", "addopts="]
    if noconftest:
        cmd.append("--noconftest")
    cmd += [str(p) for p in test_files]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return proc.returncode, (proc.stdout + "\n" + proc.stderr).strip()[-300:]
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-pairs", type=int, default=100)
    ap.add_argument("--min-lines", type=int, default=30)
    ap.add_argument("--max-lines", type=int, default=650)
    ap.add_argument("--max-attempts-per-file", type=int, default=8)
    ap.add_argument("--seed", type=int, default=2026112202)
    args = ap.parse_args()

    manifest_path = ROOT / "upstream_manifest.json"
    repos = json.loads(manifest_path.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)

    # First collect all eligible source files across repos
    eligible_files: list[dict] = []
    for repo in repos:
        repo_dir = UPSTREAM / repo["name"]
        src_dir = (repo_dir / repo["src_rel"]).resolve()
        pkg_dir = src_dir / repo["pkg_name"]
        test_dir = repo_dir / repo["test_rel"]
        if not pkg_dir.exists() or not test_dir.exists():
            continue
        for py in sorted(pkg_dir.rglob("*.py")):
            if py.name in SKIP_FILENAMES:
                continue
            if any(part.startswith("test") for part in py.relative_to(pkg_dir).parts):
                continue
            txt = py.read_text(encoding="utf-8", errors="ignore")
            nlines = txt.count("\n") + 1
            if not (args.min_lines <= nlines <= args.max_lines):
                continue
            tfiles = pick_test_files(test_dir, py.stem)
            if not tfiles:
                continue
            eligible_files.append(
                {
                    "repo": repo,
                    "repo_dir": repo_dir,
                    "src_dir": src_dir,
                    "pkg_dir": pkg_dir,
                    "py_path": py,
                    "rel_in_src": py.relative_to(src_dir).as_posix(),
                    "import_name": ".".join(py.relative_to(src_dir).with_suffix("").parts),
                    "nlines": nlines,
                    "test_files": tfiles,
                }
            )

    print(f"[volet2] Found {len(eligible_files)} eligible files across {len(repos)} repos", flush=True)
    rng.shuffle(eligible_files)

    # Track category counts to encourage balanced coverage across the 5 AST mutation classes
    cat_counts: dict[str, int] = {
        "order_boundary": 0,
        "equality_flip": 0,
        "boolean_logic": 0,
        "identity_membership": 0,
        "arithmetic_sign": 0,
    }
    accepted: list[dict] = []

    # Copy each repo once into a temp workspace so we never mutate upstream/ in place
    with tempfile.TemporaryDirectory(prefix="volet2_oracle_") as tmp_root:
        tmp_repos: dict[str, Path] = {}
        for item in eligible_files:
            if len(accepted) >= args.target_pairs:
                break
            rname = item["repo"]["name"]
            if rname not in tmp_repos:
                dst = Path(tmp_root) / rname
                shutil.copytree(item["repo_dir"], dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
                tmp_repos[rname] = dst

            work_repo = tmp_repos[rname]
            work_src = (work_repo / item["repo"]["src_rel"]).resolve()
            work_py = work_src / item["rel_in_src"]
            work_tests = [
                work_repo / tf.relative_to(item["repo_dir"]) for tf in item["test_files"]
            ]

            clean_src = work_py.read_text(encoding="utf-8")
            cands = extract_candidates(clean_src, rng)
            if not cands:
                continue

            # Baseline check: clean file MUST pass matched upstream pytest cleanly
            extra_srcs = [
                (UPSTREAM / r["name"] / r["src_rel"]).resolve()
                for r in repos
                if r["name"] != rname and (UPSTREAM / r["name"] / r["src_rel"]).exists()
            ]
            src_paths = [work_src] + extra_srcs
            use_noconf = False
            base_rc, _ = run_pytest(work_repo, src_paths, work_tests, timeout=10.0, noconftest=False)
            if base_rc != 0:
                base_rc, _ = run_pytest(work_repo, src_paths, work_tests, timeout=10.0, noconftest=True)
                use_noconf = True
            if base_rc != 0:
                continue

            # Sort candidates to favor underrepresented categories while keeping docstring priority
            cands.sort(key=lambda c: (cat_counts.get(c["category"], 0), 0 if c["has_docstring"] else 1))

            found = None
            for cand in cands[: args.max_attempts_per_file]:
                work_py.write_text(cand["mutated_src"], encoding="utf-8")
                try:
                    mut_rc, mut_out = run_pytest(work_repo, src_paths, work_tests, timeout=10.0, noconftest=use_noconf)
                finally:
                    work_py.write_text(clean_src, encoding="utf-8")
                if mut_rc == 1:
                    found = (cand, mut_out)
                    break

            if found is not None:
                cand, mut_out = found
                cat_counts[cand["category"]] = cat_counts.get(cand["category"], 0) + 1
                pair_id = f"V2P{len(accepted) + 1:03d}"
                accepted.append(
                    {
                        "pair_id": pair_id,
                        "repo": rname,
                        "commit": item["repo"]["commit"],
                        "rel_in_src": item["rel_in_src"],
                        "import_name": item["import_name"],
                        "nlines": item["nlines"],
                        "category": cand["category"],
                        "target_function": cand["function"],
                        "mutation_lineno": cand["lineno"],
                        "mutation": cand["mutation"],
                        "diff": cand["diff"],
                        "pytest_files": [tf.relative_to(item["repo_dir"]).as_posix() for tf in item["test_files"]],
                        "pytest_kill_tail": mut_out[-180:],
                        "clean_src": clean_src,
                        "buggy_src": cand["mutated_src"],
                    }
                )
                if len(accepted) % 10 == 0 or len(accepted) == args.target_pairs:
                    print(
                        f"[volet2] {len(accepted)}/{args.target_pairs} killed mutants verified | cats={cat_counts}",
                        flush=True,
                    )

    print(f"[volet2] Final accepted distinct-file pairs: {len(accepted)} | cats={cat_counts}", flush=True)
    if len(accepted) < 50:
        print("[volet2] ERROR: fewer than 50 verified pairs found!", file=sys.stderr)
        return 1

    # Snapshot clean source packages (ZERO tests/) for isolated L2 Python execution
    if PKG_STASH.exists():
        shutil.rmtree(PKG_STASH)
    PKG_STASH.mkdir(parents=True, exist_ok=True)
    used_repos = {a["repo"] for a in accepted}
    repo_by_name = {r["name"]: r for r in repos}
    pkg_roots: dict[str, Path] = {}
    for rname in sorted(used_repos):
        rinfo = repo_by_name[rname]
        src_pkg = UPSTREAM / rname / rinfo["src_rel"] / rinfo["pkg_name"]
        dst_root = PKG_STASH / rname
        shutil.copytree(
            src_pkg,
            dst_root / rinfo["pkg_name"],
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "test"),
        )
        pkg_roots[rname] = dst_root

    # Seal blind corpus
    if BLIND_DIR.exists():
        shutil.rmtree(BLIND_DIR)
    BLIND_DIR.mkdir(parents=True, exist_ok=True)

    items_to_seal = []
    for a in accepted:
        items_to_seal.append((a, "BUG", a["buggy_src"]))
        items_to_seal.append((a, "CLEAN", a["clean_src"]))

    seal_rng = random.Random(args.seed + 1)
    seal_rng.shuffle(items_to_seal)

    key_entries = []
    import_map = {}
    manifest_lines = []
    for idx, (a, label, code) in enumerate(items_to_seal, start=1):
        mod_id = f"mod_{idx:03d}"
        mod_path = BLIND_DIR / f"{mod_id}.py"
        mod_path.write_text(code, encoding="utf-8")
        digest = sha256_file(mod_path)
        manifest_lines.append(f"{digest}  blind_corpus/{mod_id}.py")
        key_entries.append(
            {
                "mod_id": mod_id,
                "pair_id": a["pair_id"],
                "label": label,
                "category": a["category"],
                "target_function": a["target_function"],
                "repo": a["repo"],
                "commit": a["commit"],
                "rel_in_src": a["rel_in_src"],
                "import_name": a["import_name"],
                "nlines": a["nlines"],
                "mutation_lineno": a["mutation_lineno"] if label == "BUG" else None,
                "mutation": a["mutation"] if label == "BUG" else None,
                "diff": a["diff"] if label == "BUG" else None,
                "pytest_files": a["pytest_files"],
                "sha256": digest,
            }
        )
        import_map[mod_id] = {
            "pkg_key": a["repo"],
            "pkg_root": str(pkg_roots[a["repo"]]),
            "import_name": a["import_name"],
            "rel_target": a["rel_in_src"],
        }

    key_path = ROOT / "key.json"
    key_path.write_text(
        json.dumps(
            {
                "bench_id": "code-bench-2026-11-22-volet2",
                "seed": args.seed,
                "n_pairs": len(accepted),
                "n_modules": len(key_entries),
                "category_counts": cat_counts,
                "entries": key_entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (ROOT / "import_map.json").write_text(json.dumps(import_map, indent=2), encoding="utf-8")
    manifest_lines.append(f"{sha256_file(key_path)}  key.json")
    manifest_lines.append(f"{sha256_file(ROOT / 'import_map.json')}  import_map.json")
    (ROOT / "MANIFEST_SEAL.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"[volet2] SEALED {len(accepted)} pairs ({len(key_entries)} blind modules) -> {BLIND_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
