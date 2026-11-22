"""Build a self-contained Colab PyTorch/HF script for Level 1 (2-pass) and Level 2 (Python exec) ablations."""
from __future__ import annotations

import argparse
import base64
import gzip
import json
from pathlib import Path

from score_bench import parse_model_json

TEMPLATE = r'''"""Self-contained Colab PyTorch/Transformers L1 & L2 ablation runner."""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PAYLOAD_B64 = """__PAYLOAD_B64__"""

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


def extract_python_block(text: str) -> str:
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()


def run_isolated_repro(mod_id: str, code: str, repro_code: str, pkg_files: dict[str, str] | None = None, rel_target: str | None = None, exec_timeout: float = 3.0) -> dict:
    with tempfile.TemporaryDirectory(prefix="repro_colab_") as tmp:
        tmp_path = Path(tmp)
        env = {
            "PATH": os.environ.get("PATH", ""),
            "TEMP": tmp,
            "TMP": tmp,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        if pkg_files and rel_target:
            pkg_dst = tmp_path / "pkg_env"
            for rpath, content in pkg_files.items():
                fp = pkg_dst / rpath
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content, encoding="utf-8")
            tfile = pkg_dst / rel_target
            tfile.parent.mkdir(parents=True, exist_ok=True)
            tfile.write_text(code, encoding="utf-8")
            env["PYTHONPATH"] = str(pkg_dst)
        else:
            (tmp_path / f"{mod_id}.py").write_text(code, encoding="utf-8")
            env["PYTHONPATH"] = str(tmp_path)

        script_path = tmp_path / "_repro_check.py"
        script_path.write_text(repro_code, encoding="utf-8")
        t0 = time.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
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
        return {
            "returncode": rc,
            "timed_out": timed_out,
            "elapsed_sec": round(time.perf_counter() - t0, 3),
            "stdout": stdout,
            "stderr": stderr,
        }


def generate_batch(model, tokenizer, messages_list: list[list[dict]], batch_size: int, max_new_tokens: int) -> list[str]:
    import torch

    prompts = [
        tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        for msgs in messages_list
    ]
    # Length-sort to eliminate padding waste & prevent OOM on long real-world modules
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
    outputs = [""] * len(prompts)
    pos = 0
    while pos < len(order):
        cur_bs = min(batch_size, len(order) - pos)
        idxs = order[pos : pos + cur_bs]
        chunk = [prompts[i] for i in idxs]
        try:
            enc = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=8192).to(model.device)
            in_len = enc["input_ids"].shape[1]
            with torch.inference_mode():
                gen = model.generate(
                    **enc,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if cur_bs == 1:
                raise
            cur_bs = 1
            idxs = order[pos : pos + 1]
            chunk = [prompts[idxs[0]]]
            enc = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=6144).to(model.device)
            in_len = enc["input_ids"].shape[1]
            with torch.inference_mode():
                gen = model.generate(
                    **enc,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
        for j, orig_i in enumerate(idxs):
            out_ids = gen[j][in_len:]
            outputs[orig_i] = tokenizer.decode(out_ids, skip_special_tokens=True).strip()
        del enc, gen
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        pos += cur_bs
    return outputs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    payload = json.loads(gzip.decompress(base64.b64decode(PAYLOAD_B64)).decode("utf-8"))
    items = payload["items"]
    pkg_bundles = payload.get("pkg_bundles", {})
    flagged = [it for it in items if it["l0_is_bug"]]
    print(f"[colab-ablation] loaded {len(items)} items ({len(flagged)} flagged in L0)", file=sys.stderr, flush=True)

    if args.dry_run:
        # Test isolated repro execution mechanically
        r = run_isolated_repro("demo_mod", "def f(x):\n    return x + 1\n", "import demo_mod\nassert demo_mod.f(1) == 2\n")
        assert r["returncode"] == 0, r
        print("DRY_RUN_OK", file=sys.stderr, flush=True)
        return 0

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dev_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    vram_gb = (torch.cuda.get_device_properties(0).total_memory / (1024**3)) if torch.cuda.is_available() else 0.0
    print(f"[colab-ablation] Device={dev_name} ({vram_gb:.1f}GB) loading {args.model}...", file=sys.stderr, flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    load_kwargs: dict = {"device_map": "auto", "trust_remote_code": True}
    if torch.cuda.is_available() and "14B" in args.model and vram_gb < 32.0:
        import logging
        try:
            import bitsandbytes  # noqa: F401
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "bitsandbytes"])
        logging.getLogger("bitsandbytes").setLevel(logging.ERROR)
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16
        )
        print("[colab-ablation] Using bitsandbytes NF4 4-bit quantization for 14B on <32GB GPU", file=sys.stderr, flush=True)
    else:
        load_kwargs["dtype"] = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.model, **load_kwargs)
    model.eval()

    # --- LEVEL 1: Adversarial 2-pass ---
    l1_msgs = []
    for it in flagged:
        u = (
            f"Module `{it['mod_id']}.py`:\n\n```python\n{it['code']}\n```\n\n"
            f"Initial reviewer's bug claim:\n```json\n{it['claim_json']}\n```\n\n"
            "Try to falsify this claim against the actual code and specification. "
            "Return ONLY the JSON verdict object."
        )
        l1_msgs.append([{"role": "system", "content": L1_SYSTEM_PROMPT}, {"role": "user", "content": u}])
    t0 = time.perf_counter()
    l1_outs = generate_batch(model, tokenizer, l1_msgs, args.batch_size, 320) if flagged else []
    print(f"[colab-ablation] L1 done ({len(l1_outs)} flagged) in {round(time.perf_counter()-t0, 1)}s", file=sys.stderr, flush=True)
    l1_map = {it["mod_id"]: out for it, out in zip(flagged, l1_outs)}

    # --- LEVEL 2 Step 1: Repro synthesis ---
    l2_repro_msgs = []
    for it in flagged:
        imp_hint = (
            f"Import the target using `import {it['import_name']}` (the package is on PYTHONPATH)."
            if it.get("pkg_key")
            else f"Import the module using `import {it['mod_id']}` (the file `{it['mod_id']}.py` is on PYTHONPATH)."
        )
        u = (
            f"Module `{it['mod_id']}.py`:\n\n```python\n{it['code']}\n```\n\n"
            f"Initial reviewer's bug claim:\n```json\n{it['claim_json']}\n```\n\n"
            f"{imp_hint}\n"
            "Write a concise verification script (<= 40 lines) that asserts the specification "
            "behavior on the claimed failing input. Return ONLY one ```python ... ``` block."
        )
        l2_repro_msgs.append([{"role": "system", "content": L2_REPRO_SYSTEM_PROMPT}, {"role": "user", "content": u}])
    t1 = time.perf_counter()
    l2_repro_raw = generate_batch(model, tokenizer, l2_repro_msgs, args.batch_size, 512) if flagged else []
    print(f"[colab-ablation] L2 repro synthesis done in {round(time.perf_counter()-t1, 1)}s", file=sys.stderr, flush=True)

    # --- LEVEL 2 Step 2: Isolated execution ---
    repro_codes = []
    exec_results = []
    for it, raw_r in zip(flagged, l2_repro_raw):
        rc_code = extract_python_block(raw_r)
        repro_codes.append(rc_code)
        pkg_files = pkg_bundles.get(it["pkg_key"]) if it.get("pkg_key") else None
        ex = run_isolated_repro(it["mod_id"], it["code"], rc_code, pkg_files=pkg_files, rel_target=it.get("rel_target"), exec_timeout=3.0)
        exec_results.append(ex)
    print(f"[colab-ablation] L2 isolated exec done ({len(exec_results)} scripts)", file=sys.stderr, flush=True)

    # --- LEVEL 2 Step 3: Evidence-grounded verdict ---
    l2_verdict_msgs = []
    for it, rc_code, ex in zip(flagged, repro_codes, exec_results):
        u = (
            f"Module `{it['mod_id']}.py`:\n\n```python\n{it['code']}\n```\n\n"
            f"Initial reviewer's bug claim:\n```json\n{it['claim_json']}\n```\n\n"
            f"Executed Python verification script:\n```python\n{rc_code}\n```\n\n"
            f"Observed execution result:\n```json\n{json.dumps(ex, ensure_ascii=False, indent=2)}\n```\n\n"
            "Based on the code, specification, script, and observed execution output, "
            "return ONLY the final JSON verdict object."
        )
        l2_verdict_msgs.append([{"role": "system", "content": L2_VERDICT_SYSTEM_PROMPT}, {"role": "user", "content": u}])
    t2 = time.perf_counter()
    l2_outs = generate_batch(model, tokenizer, l2_verdict_msgs, args.batch_size, 320) if flagged else []
    print(f"[colab-ablation] L2 verdicts done in {round(time.perf_counter()-t2, 1)}s", file=sys.stderr, flush=True)
    l2_map = {
        it["mod_id"]: {"raw_output": out, "repro_code": rcode, "exec_result": ex}
        for it, out, rcode, ex in zip(flagged, l2_outs, repro_codes, exec_results)
    }

    passthrough = json.dumps({
        "verdict": "CLEAN",
        "bug_function": None,
        "bug_line_approx": None,
        "explanation": "L0 predicted CLEAN (or unparseable); passed through by pre-registered gate.",
    })

    for it in items:
        mid = it["mod_id"]
        if mid in l1_map:
            rec1 = {"mod_id": mid, "model": args.model, "level": "l1", "skipped_clean_in_l0": False, "raw_output": l1_map[mid]}
            rec2 = {
                "mod_id": mid, "model": args.model, "level": "l2", "skipped_clean_in_l0": False,
                "raw_output": l2_map[mid]["raw_output"],
                "repro_code": l2_map[mid]["repro_code"],
                "exec_result": l2_map[mid]["exec_result"],
            }
        else:
            rec1 = {"mod_id": mid, "model": args.model, "level": "l1", "skipped_clean_in_l0": True, "raw_output": passthrough}
            rec2 = {"mod_id": mid, "model": args.model, "level": "l2", "skipped_clean_in_l0": True, "raw_output": passthrough}
        print("L1_RECORD:" + json.dumps(rec1, ensure_ascii=False), flush=True)
        print("L2_RECORD:" + json.dumps(rec2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blind-dir", type=Path, required=True)
    ap.add_argument("--l0", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--import-map", type=Path, default=None)
    args = ap.parse_args()

    l0_map = {}
    for ln in args.l0.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            l0_map[r["mod_id"]] = r

    import_map = (
        json.loads(args.import_map.read_text(encoding="utf-8"))
        if args.import_map and args.import_map.exists()
        else {}
    )
    pkg_bundles: dict[str, dict[str, str]] = {}
    items = []
    for p in sorted(args.blind_dir.glob("mod_*.py")):
        mid = p.stem
        parsed = parse_model_json(l0_map[mid].get("raw_output", ""))
        is_bug = bool(parsed and parsed["verdict"] == "BUG")
        claim_json = ""
        if is_bug:
            raw_obj = parsed.get("raw_parsed", {})
            claim_json = json.dumps(
                {
                    "verdict": "BUG",
                    "bug_function": parsed.get("bug_function"),
                    "bug_line_approx": raw_obj.get("bug_line_approx"),
                    "explanation": raw_obj.get("explanation", ""),
                },
                ensure_ascii=False,
                indent=2,
            )
        item = {
            "mod_id": mid,
            "code": p.read_text(encoding="utf-8"),
            "l0_is_bug": is_bug,
            "claim_json": claim_json,
        }
        if mid in import_map:
            im = import_map[mid]
            pk = im["pkg_key"]
            item["pkg_key"] = pk
            item["import_name"] = im["import_name"]
            item["rel_target"] = im["rel_target"]
            if pk not in pkg_bundles:
                root = Path(im["pkg_root"])
                bundle = {}
                for fp in root.rglob("*.py"):
                    rel = fp.relative_to(root).as_posix()
                    bundle[rel] = fp.read_text(encoding="utf-8", errors="replace")
                pkg_bundles[pk] = bundle
        items.append(item)

    raw_bytes = gzip.compress(
        json.dumps({"items": items, "pkg_bundles": pkg_bundles}, ensure_ascii=False).encode("utf-8"),
        compresslevel=9,
    )
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    script = TEMPLATE.replace("__PAYLOAD_B64__", b64)
    args.out.write_text(script, encoding="utf-8")
    print(f"BUILT {args.out} ({len(items)} items, {sum(x['l0_is_bug'] for x in items)} flagged, {len(script)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
