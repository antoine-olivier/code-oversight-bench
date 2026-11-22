"""Build a self-contained Colab GPU runner using native PyTorch + Transformers (no vLLM install/JIT)."""
from __future__ import annotations

import argparse
import base64
import json
import zlib
from pathlib import Path

SYSTEM_PROMPT = (
    "You are an independent Python code reviewer. Review the Python code below "
    "for genuine functional or security bugs (ignore style preferences, missing optional "
    "features, or formatting). Reply ONLY with a single JSON object matching this exact schema:\n"
    '{"verdict": "BUG" | "CLEAN", "bug_function": "<function_name or null>", '
    '"bug_line_approx": <integer or null>, "explanation": "<1-3 concise sentences>"}'
)

TEMPLATE = r'''"""Self-contained Colab GPU evaluator using pre-installed PyTorch + Transformers."""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import zlib

SYSTEM_PROMPT = __SYSTEM_PROMPT__
PAYLOAD_B64 = __PAYLOAD_B64__


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=220)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    items = json.loads(zlib.decompress(base64.b64decode(PAYLOAD_B64)).decode("utf-8"))
    if args.dry_run:
        print(f"DRY_RUN OK: {len(items)} blind items ready for {args.model}")
        return 0

    t0 = time.perf_counter()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    vram_gb = (torch.cuda.get_device_properties(0).total_memory / (1024**3)) if torch.cuda.is_available() else 0.0
    print(f"[colab-hf] Device={device_name} ({vram_gb:.1f}GB) loading {args.model}...", file=sys.stderr, flush=True)

    t_load0 = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(args.model, padding_side="left")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    load_kwargs = {"device_map": "auto"}
    if torch.cuda.is_available() and "14B" in args.model and vram_gb < 32.0:
        import logging, subprocess
        try:
            import bitsandbytes  # noqa: F401
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "bitsandbytes"])
        logging.getLogger("bitsandbytes").setLevel(logging.ERROR)
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16
        )
        print("[colab-hf] Using bitsandbytes NF4 4-bit quantization for 14B on <32GB GPU", file=sys.stderr, flush=True)
    else:
        load_kwargs["dtype"] = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.model, **load_kwargs)
    model.eval()
    load_s = time.perf_counter() - t_load0

    # Sort by length to avoid padding waste and prevent OOM on long real-world modules
    indexed = sorted(enumerate(items), key=lambda kv: len(kv[1]["code"]))
    sorted_items = [kv[1] for kv in indexed]

    prompts = []
    for item in sorted_items:
        user_msg = (
            f"Module `{item['mod_id']}.py`:\n\n```python\n{item['code']}\n```\n\n"
            "Return ONLY the JSON verdict object."
        )
        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        prompts.append(tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True))

    t_gen0 = time.perf_counter()
    records = []
    bs = args.batch_size
    start = 0
    while start < len(prompts):
        cur_bs = bs
        batch_prompts = prompts[start : start + cur_bs]
        batch_items = sorted_items[start : start + cur_bs]
        try:
            enc = tokenizer(batch_prompts, return_tensors="pt", padding=True, truncation=True, max_length=8192).to(model.device)
            in_len = enc["input_ids"].shape[1]
            with torch.inference_mode():
                gen = model.generate(
                    **enc,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                )
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if cur_bs == 1:
                raise
            cur_bs = 1
            batch_prompts = prompts[start : start + 1]
            batch_items = sorted_items[start : start + 1]
            enc = tokenizer(batch_prompts, return_tensors="pt", padding=True, truncation=True, max_length=6144).to(model.device)
            in_len = enc["input_ids"].shape[1]
            with torch.inference_mode():
                gen = model.generate(
                    **enc,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                )
        for idx, item in enumerate(batch_items):
            out_ids = gen[idx][in_len:]
            text = tokenizer.decode(out_ids, skip_special_tokens=True).strip()
            records.append(
                {
                    "mod_id": item["mod_id"],
                    "model": args.model,
                    "raw_output": text,
                    "prompt_tokens": int(enc["attention_mask"][idx].sum().item()),
                    "output_tokens": int(len(out_ids)),
                }
            )
        del enc, gen
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        start += cur_bs
        print(f"[colab-hf] {min(start, len(prompts))}/{len(prompts)} done", file=sys.stderr, flush=True)
    records.sort(key=lambda r: r["mod_id"])
    gen_s = time.perf_counter() - t_gen0

    print("===COLAB_META===")
    print(json.dumps({
        "model": args.model,
        "device": device_name,
        "count": len(items),
        "load_sec": round(load_s, 1),
        "gen_sec": round(gen_s, 1),
        "total_sec": round(time.perf_counter() - t0, 1),
    }))
    print("===END_COLAB_META===")
    print("===BEGIN_JSONL===")
    for rec in records:
        print(json.dumps(rec, ensure_ascii=False))
    print("===END_JSONL===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blind-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    mods = sorted(args.blind_dir.glob("mod_*.py"))
    assert mods, f"No mod_*.py found in {args.blind_dir}"
    items = [{"mod_id": p.stem, "code": p.read_text(encoding="utf-8")} for p in mods]
    raw_bytes = json.dumps(items, ensure_ascii=False).encode("utf-8")
    b64 = base64.b64encode(zlib.compress(raw_bytes, level=9)).decode("ascii")
    script = TEMPLATE.replace("__SYSTEM_PROMPT__", repr(SYSTEM_PROMPT)).replace("__PAYLOAD_B64__", repr(b64))
    args.out.write_text(script, encoding="utf-8")
    print(f"BUILT {args.out.name}: {len(mods)} blind modules, {len(script)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
