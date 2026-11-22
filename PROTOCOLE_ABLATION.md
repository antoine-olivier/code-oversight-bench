# Pre-registered Ablation Protocol — `code-bench-2026-11-22`

Registered before running any Level 1 or Level 2 inference.

## Objective

Test whether structured oversight harnesses reduce false-positive collapse while preserving true-positive bug detection on the **exact same sealed blind corpora** as Level 0 (bare):
- **Volet 1 (`n = 30` matched pairs = 60 standalone Python modules, 6 classes)** — sealed in `MANIFEST_SEAL.sha256`.
- **Volet 2 (`n = 100` matched pairs = 200 real MIT/BSD open-source Python files, single-line AST mutations mechanically verified by upstream `pytest`)** — sealed in `volet2/MANIFEST_SEAL.sha256`.

## Three-Level Escalating Harness (Ablation 0 -> 1 -> 2)

All levels read the exact same blind files (`mod_*.py`) and never see ground-truth keys, upstream test suites, or pair pairings.

### Level 0 — Bare (`L0_bare`)
- Single pass, neutral system prompt, zero tools (`--tools ""`, `--setting-sources project`, `--strict-mcp-config`, empty cwd, `MAX_THINKING_TOKENS=0` for Claude; greedy `do_sample=False` chat template for open-weights on Colab).
- Output schema: `{"verdict": "BUG"|"CLEAN", "bug_function": str|null, "bug_line_approx": int|null, "explanation": str}`.

### Level 1 — Adversarial 2-Pass (`L1_adversarial_2pass`, zero tools)
- Input: Level 0 prediction on `mod_X.py`.
- If Level 0 predicted `CLEAN` (or failed to parse): verdict remains `CLEAN` (Level 1 acts strictly as a falsification gate on flagged modules, isolating precision/FPR control without shifting recall by re-prompting clean modules).
- If Level 0 predicted `BUG`: a **fresh blind skeptical reviewer** (zero conversation history from L0, zero tools) receives `mod_X.py` and L0's claim (`bug_function`, `bug_line_approx`, `explanation`). Its mandate is to **try to falsify the claim** against the actual code and docstring/contract: check whether the alleged bug is actually permitted by the specification, misreads Python semantics, is unreachable, or is a genuine specification violation.
- Output schema: identical JSON (`BUG` = claim survived falsification; `CLEAN` = claim refuted as false positive).

### Level 2 — Adversarial + Isolated Python Execution (`L2_python_exec`)
- Input: Level 0 prediction on `mod_X.py` (independent of L1 so `L0 -> L1`, `L0 -> L2`, and `L1 vs L2` are directly comparable on the exact same flagged subset; `L1 ∩ L2` is also computable deterministically without extra calls).
- If Level 0 predicted `CLEAN` (or failed to parse): verdict remains `CLEAN`.
- If Level 0 predicted `BUG`:
  1. **Repro synthesis:** A fresh call receives `mod_X.py` and L0's claim and writes a short, self-contained Python verification script (`<= 40` lines) that imports the blind module (`import mod_X` for Volet 1; target module on isolated package `PYTHONPATH` with zero upstream tests for Volet 2), invokes the suspect function on a concrete input that violates the specification, and raises `AssertionError` if the bug is present (exits 0 if the code behaves per specification).
  2. **Isolated execution:** The harness runs the script in an isolated subprocess (`python -I`, temp cwd, `PYTHONDONTWRITEBYTECODE=1`, 3.0s timeout, truncated stdout/stderr <= 2000 chars).
  3. **Evidence-grounded verdict:** A fresh verifier call receives `mod_X.py`, L0's claim, the executed repro script, and the observed `(returncode, stdout, stderr, timed_out)` and renders the final JSON verdict (`BUG` only if execution confirms a genuine specification violation; `CLEAN` if the code behaved per spec or the repro failed to demonstrate a real bug).

## Pre-registered Primary Metrics & Comparisons

- Primary metrics (identical to `PROTOCOLE.md`): **Strict TPR**, **FPR**, **Strict Paired Separation**, **Balanced Accuracy**, all with Wilson 95% CIs and paired bootstrap 95% CIs (2,000 draws, seed 0).
- Primary paired contrasts (paired bootstrap 95% CI excluding 0 = **established**):
  - `L1 - L0` (pure text adversarial review effect on FPR, TPR, Strict Paired Separation).
  - `L2 - L0` (isolated Python execution verification effect on FPR, TPR, Strict Paired Separation).
  - `L2 - L1` (incremental gain of mechanical execution over text-only adversarial review).
- Models:
  - Volet 1: `Qwen2.5-Coder-7B-Instruct` (Colab L4, L0/L1/L2), `claude-haiku-4-5` (L0/L1/L2), `claude-sonnet-5-5` (L0/L1/L2).
  - Volet 2: `Qwen2.5-Coder-7B-Instruct` (Colab L4, L0/L1/L2), `claude-haiku-4-5` (L0/L1/L2), `claude-sonnet-5-5` (L0 ceiling; L1/L2 if Claude 5h quota permits).
