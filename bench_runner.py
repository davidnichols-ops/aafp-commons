#!/usr/bin/env python3
"""Bench runner: executes the frozen bench contract and produces a signed artifact.

Usage:
  python3 bench_runner.py --root /root/commons-data --recipe protocols/bench-llama8b-q4-toks.json

Uses transformers + bitsandbytes for Q4 quantization on GPU.
Downloads model weights ONCE, hashes them, runs the bench, produces an artifact.
Does NOT propose — the caller uses the digest in /propose.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR / "src"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def get_gpu_name() -> str:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return out.split("\n")[0] if out else "unknown"
    except Exception:
        return "unknown"


def download_model(model_dir: Path) -> tuple[Path, str]:
    """Download model from HuggingFace and return (path, weights_digest).

    Uses Q4 quantization via bitsandbytes, so we download the original
    safetensors weights and quantize at load time. The weights digest
    is the sha256 of the downloaded safetensors files.
    """
    from huggingface_hub import snapshot_download

    model_dir.mkdir(parents=True, exist_ok=True)
    repo_id = "NousResearch/Meta-Llama-3-8B-Instruct"

    # Check if already downloaded
    cache_dir = model_dir / "Meta-Llama-3-8B-Instruct"
    if cache_dir.exists() and any(cache_dir.glob("*.safetensors")):
        print(f"[bench] model already cached at {cache_dir}")
    else:
        print(f"[bench] downloading {repo_id}...")
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(cache_dir),
            local_dir_use_symlinks=False,
            allow_patterns=["*.safetensors", "*.json", "tokenizer*", "special_tokens*"],
        )
        print(f"[bench] downloaded to {cache_dir}")

    # Hash all safetensors files
    safetensors = sorted(cache_dir.glob("*.safetensors"))
    if not safetensors:
        print("[bench] ERROR: no safetensors files found")
        sys.exit(1)

    h = hashlib.sha256()
    for st in safetensors:
        with open(st, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    weights_digest = f"sha256:{h.hexdigest()}"
    print(f"[bench] weights_digest={weights_digest}")

    return cache_dir, weights_digest


def run_bench(
    model_path: Path,
    prompt: str,
    max_tokens: int,
    seed: int,
    warmup: int,
) -> tuple[float, str]:
    """Run benchmark with Q4 quantization. Returns (tok_s, raw_log)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    print(f"[bench] loading model with Q4 quantization from {model_path}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
    )
    model.eval()

    # Apply chat template
    messages = [{"role": "user", "content": prompt}]
    input_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    # Only pass known keys to generate()
    gen_inputs = {
        k: v for k, v in inputs.items()
        if k in ("input_ids", "attention_mask", "token_type_ids")
    }

    # Warmup runs
    for i in range(warmup):
        print(f"[bench] warmup {i + 1}/{warmup}")
        torch.manual_seed(seed)
        with torch.no_grad():
            _ = model.generate(
                **gen_inputs,
                max_new_tokens=16,
                do_sample=False,
            )
        torch.cuda.synchronize()

    # Measured runs
    tok_s_values = []
    log_lines = []
    for i in range(3):
        torch.cuda.synchronize()
        torch.manual_seed(seed)
        t0 = time.time()
        with torch.no_grad():
            output = model.generate(
                **gen_inputs,
                max_new_tokens=max_tokens,
                do_sample=False,
            )
        torch.cuda.synchronize()
        elapsed = time.time() - t0

        # Count generated tokens (exclude prompt)
        input_len = inputs["input_ids"].shape[1]
        generated_len = output.shape[1] - input_len
        rate = generated_len / elapsed if elapsed > 0 else 0
        tok_s_values.append(rate)
        log_lines.append(
            f"run {i + 1}: tokens={generated_len} "
            f"elapsed={elapsed:.3f}s tok/s={rate:.2f}"
        )
        print(f"[bench] run {i + 1}: {rate:.2f} tok/s")

    mean_tok_s = sum(tok_s_values) / len(tok_s_values)
    raw_log = "\n".join(log_lines) + f"\nmean_tok_s={mean_tok_s:.2f}\n"
    return mean_tok_s, raw_log


def main():
    parser = argparse.ArgumentParser(
        description="Run frozen bench and produce signed artifact"
    )
    parser.add_argument("--root", required=True, help="commons data root")
    parser.add_argument("--recipe", required=True, help="path to bench contract JSON")
    args = parser.parse_args()

    root = Path(args.root)
    recipe_path = Path(args.recipe)

    # Load recipe
    with open(recipe_path) as f:
        recipe = json.load(f)

    recipe_digest = sha256_file(recipe_path)
    print(f"[bench] recipe_digest={recipe_digest}")

    # Download model
    model_dir = root / "models"
    model_path, weights_digest = download_model(model_dir)

    # Run bench
    gpu_name = get_gpu_name()
    host = platform.node()
    prompt = recipe["prompt"]["text"]
    max_tokens = recipe["prompt"]["max_tokens"]
    seed = recipe["prompt"]["seed"]
    warmup = recipe["runtime"]["warmup_runs"]

    tok_s, raw_log = run_bench(model_path, prompt, max_tokens, seed, warmup)
    raw_log_digest = sha256_bytes(raw_log.encode())

    # Build artifact
    artifact = {
        "kind": "evidence",
        "uri": "commons/artifact/PLACEHOLDER",
        "host": host,
        "gpu_name": gpu_name,
        "recipe_digest": recipe_digest,
        "tok_s": round(tok_s, 2),
        "raw_log_digest": raw_log_digest,
        "weights_digest": weights_digest,
        "raw_log": raw_log,
    }

    # Content-address the artifact (without the uri placeholder)
    artifact_for_hash = {k: v for k, v in artifact.items() if k != "uri"}
    artifact_bytes = json.dumps(artifact_for_hash, sort_keys=True).encode()
    artifact_digest = sha256_bytes(artifact_bytes)
    artifact["uri"] = f"commons/artifact/{artifact_digest.removeprefix('sha256:')}"

    # Store artifact
    objects_dir = root / "objects"
    objects_dir.mkdir(exist_ok=True)
    artifact_path = objects_dir / f"{artifact_digest.removeprefix('sha256:')}.json"
    with open(artifact_path, "w") as f:
        json.dump(artifact, f, sort_keys=True, indent=2)
    print(f"[bench] artifact stored: {artifact_path}")
    print(f"[bench] artifact_digest={artifact_digest}")
    print(f"[bench] tok_s={tok_s:.2f}")

    # Print for the caller
    print(f"ARTIFACT_DIGEST={artifact_digest}")
    print(f"TOK_S={tok_s:.2f}")
    print(f"RECIPE_DIGEST={recipe_digest}")


if __name__ == "__main__":
    main()
