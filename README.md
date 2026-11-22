# `code-bench-2026-11-22`: Matched-Pair Code Oversight & Harness Ablation Benchmark

Reproducible matched-pair benchmark measuring false-alarm collapse, scaling, and oversight-harness ablations (`L0` bare -> `L1` adversarial 2-pass -> `L2` isolated Python execution) across 4 models (`Qwen2.5-Coder-7B-Instruct`, `Qwen2.5-Coder-14B-Instruct`, `Claude Haiku 4.5`, `Claude Sonnet 5.5`) and 2 complementary sealed blind corpora (`130` matched pairs = `260` blind Python modules, `3,120` blind module-arm evaluations):

- **Volet 1 (`n = 30` pairs / `60` modules):** Freshly authored standalone Python modules across 6 safety/correctness classes (`guard_access`, `stats_eval`, `numeric_math`, `state_cache`, `parsing_bounds`, `security_integrity`), mechanically verified by general + trigger tests (`verify_corpus.py`), SHA-256 sealed before inference.
- **Volet 2 (`n = 100` pairs / `200` modules):** 100 distinct real-world production `.py` files (30–650 lines) from 15 MIT/BSD/Apache libraries, with single-line surgical AST mutations (`order_boundary`, `equality_flip`, `boolean_logic`, `identity_membership`, `arithmetic_sign`) mechanically killed (`rc == 1`) by upstream `pytest`, SHA-256 sealed before inference. To avoid redistributing third-party source files, `volet2/blind_corpus/` is omitted from the public repo and can be reconstructed byte-identically from the pinned upstream commits (`volet2/upstream_manifest.json`) via `python volet2/fetch_repos.py && python volet2/build_volet2.py` and verified against `volet2/MANIFEST_SEAL.sha256`.

See [`REPORT.md`](REPORT.md) for the complete empirical results, Wilson/paired-bootstrap 95% CIs, and mechanistic error analysis, and [`PROTOCOLE.md`](PROTOCOLE.md) / [`PROTOCOLE_ABLATION.md`](PROTOCOLE_ABLATION.md) for pre-registered protocols.

## Quick Verification

```bash
python verify_corpus.py
python score_bench.py --selftest
python run_ablation_claude.py --selftest
python dump_tables.py runs/score-volet1-12arms.json volet2/runs/score-v2-12arms.json
```
