# Protocol — Planted-Bug Code Oversight Bench (`code-bench-2026-11-22`)

**Status:** Pre-registered before any model call or blinding seal.
**Author:** Antoine Olivier (experimental design, class selection, freeze approval; Claude/Antigravity agents wrote the corpus modules and evaluation scripts under direction).

## 1. Research Question
Given a standalone Python module (with a clear docstring specification and no test suite), can an AI code reviewer distinguish clean control modules from matched modules containing one realistic, test-verified planted bug — without false alarms on the clean controls?

## 2. Corpus Design (30 matched pairs = 60 modules)
- **Size:** `n = 30` matched pairs (30 clean controls + 30 planted-bug copies = 60 standalone stdlib Python modules).
- **Six bug classes (5 pairs each):**
  1. `guard_access`: path/prefix/allowlist/fail-open guard bugs.
  2. `stats_eval`: ML/statistical evaluation bugs (leakage, quantile threshold, cluster bootstrap, weighting, NaN handling).
  3. `numeric_math`: numerical & exact-math bugs (cancellation, integer truncation, gradient projection, interval bounds, matrix order).
  4. `state_cache`: state/caching bugs (mutable default, cache key collision, non-atomic write, shallow aliasing, stale memoization).
  5. `parsing_bounds`: parsing & boundary bugs (CSV/quoting, BOM/UTF-8, window slicing, binary search boundary, timestamp/UTC handling).
  6. `security_integrity`: integrity & security bugs (hash truncation, manifest dotfile skip, schema extra-key bypass, rate-limiter reset, canonical path check).
- **Mechanical ground-truth gate (`verify_corpus.py`, required 30/30 PASS before sealing):**
  - Each pair provides `clean_code`, `buggy_code`, `target_function`, `general_tests`, and `trigger_test`.
  - `clean_code` passes 100% of `general_tests` AND `trigger_test`.
  - `buggy_code` passes 100% of `general_tests` (plausible, syntactically valid, non-crashing on normal inputs) AND fails `trigger_test` (proves the bug violates the docstring spec).
  - Diff between `clean_code` and `buggy_code` is strictly localized (1 to 6 changed lines) inside `target_function`.
  - Zero benchmark-hint tokens (`bug`, `planted`, `bench`, `fault`, `inject`, `trap`, `clean_code`, `buggy_code`) in any module source.

## 3. Blinding & Cryptographic Sealing (`seal_bench.py`)
- All 60 modules are shuffled with fixed seed `20261122` into neutral filenames `mod_01.py` .. `mod_60.py` inside `blind_corpus/`.
- SHA-256 hashes of `PROTOCOLE.md`, `verify_corpus.py`, `score_bench.py`, `key.json`, and all 60 blind files are recorded in `MANIFEST_SEAL.sha256` before any model arm executes.
- Reviewer prompt is identical across all 60 files and all arms, with zero mention of a benchmark, planted errors, or pair structure.

## 4. Model Arms (frozen before execution)
- **Arm A (Open-Weights Colab A100 via offline vLLM):** `Qwen/Qwen2.5-Coder-14B-Instruct` (Apache-2.0, `temperature = 0.0`, `max_tokens = 384`, 0 tools).
- **Arm B (Frontier Claude via CLI, tools disabled):** `claude-haiku-4-5` (and optionally `claude-sonnet-4-5` if quota permits, recorded as Arm C), `tools = ""`, no filesystem access.
- Every raw output is saved verbatim in `runs/<arm>/raw.jsonl`. Parse failures are counted explicitly and never silently dropped or retried selectively.

## 5. Primary & Secondary Metrics (`score_bench.py`)
1. **Strict TPR (primary detection):** share of 30 buggy modules where `verdict == "BUG"` AND `bug_function == target_function`.
2. **Verdict-only TPR:** share of 30 buggy modules where `verdict == "BUG"`.
3. **FPR (primary false-alarm rate):** share of 30 clean modules where `verdict == "BUG"`.
4. **Strict Paired Separation (primary discrimination):** share of 30 pairs where buggy copy gets `(BUG, target_function)` AND matched clean copy gets `CLEAN`.
5. **Verdict Paired Separation:** share of 30 pairs where buggy copy gets `BUG` AND matched clean copy gets `CLEAN`.
6. **Balanced Accuracy (verdict):** `0.5 * (verdict_TPR + (1 - FPR))`.
7. **Uncertainty:** 95% Wilson intervals for proportions and 95% paired bootstrap intervals by pair (2,000 draws, seed 0) for each metric and for cross-arm paired differences. A cross-arm difference is labeled "established" only if its 95% paired bootstrap CI excludes 0.

## 6. Explicit Limits (to be stated with any result)
- Authored single-file Python modules (60–110 lines), not multi-file production repositories.
- Single zero-shot prompt, deterministic decoding (`temperature = 0` where supported), single trial per module.
- `n = 30` pairs: confidence intervals remain ~15–20 percentage points wide; per-class counts (`n = 5`) are purely descriptive.
- Modules were authored by AI under the researcher's direction and checked mechanically by unit tests, not sampled from real-world CVE commits.
