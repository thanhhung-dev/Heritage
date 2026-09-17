#!/usr/bin/env python3
"""Merge a PEFT adapter into its Hugging Face base model and export GGUF.

Run in the training environment after LoRA finishes:
    python scripts/export_gguf.py

The script needs internet once to clone llama.cpp and install its converter
requirements. Temporary merged weights and converter files are removed afterwards.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
ADAPTER_PATH = MODELS_DIR / "peft-adapter"
OUTPUT_PATH = MODELS_DIR / "qwen-fused.gguf"


def run(*args: str, cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def converter_requirements(llama_cpp: Path) -> Path:
    candidates = [
        llama_cpp / "requirements" / "requirements-convert_hf_to_gguf.txt",
        llama_cpp / "requirements.txt",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("Không tìm thấy requirements cho convert_hf_to_gguf.py")


def resolve_adapter_path(adapter: Path, checkpoint: str | None) -> Path:
    """Resolve the final PEFT adapter or one Trainer checkpoint."""
    selected = adapter
    if checkpoint:
        step = checkpoint.removeprefix("checkpoint-")
        selected = adapter / f"checkpoint-{step}"
    config = selected / "adapter_config.json"
    if not config.is_file():
        raise FileNotFoundError(f"Thiếu {config}")
    return selected


def merge_peft_adapter(adapter: Path, output: Path) -> str:
    """Merge an unquantized FP16 base model with the selected PEFT adapter."""
    import torch
    from peft import PeftConfig, PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    peft_config = PeftConfig.from_pretrained(adapter)
    base_model = peft_config.base_model_name_or_path
    print(f"Base model từ adapter_config: {base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    model = PeftModel.from_pretrained(model, adapter)
    merged = model.merge_and_unload(safe_merge=True)
    merged.save_pretrained(output, safe_serialization=True, max_shard_size="4GB")
    tokenizer = AutoTokenizer.from_pretrained(adapter, use_fast=True)
    tokenizer.save_pretrained(output)
    return str(base_model)


def export(adapter: Path, output: Path, force: bool) -> None:
    if output.exists() and not force:
        print(f"Đã có {output}. Dùng --force nếu muốn tạo lại.")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    with tempfile.TemporaryDirectory(prefix="heritagegraph-gguf-") as directory:
        workspace = Path(directory)
        fp16_model = workspace / "qwen-merged-fp16"
        llama_cpp = workspace / "llama.cpp"
        converter_venv = workspace / "converter-venv"

        print("[1/4] Merge PEFT adapter vào base model FP16...")
        merge_peft_adapter(adapter, fp16_model)

        print("[2/4] Tải llama.cpp converter...")
        run(
            "git",
            "clone",
            "--depth",
            "1",
            "https://github.com/ggml-org/llama.cpp.git",
            str(llama_cpp),
        )

        print("[3/4] Cài dependency converter trong môi trường tạm...")
        run(sys.executable, "-m", "venv", str(converter_venv))
        converter_python = converter_venv / "bin" / "python"
        if sys.platform == "win32":
            converter_python = converter_venv / "Scripts" / "python.exe"
        run(
            str(converter_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            str(converter_requirements(llama_cpp)),
        )

        print("[4/4] Chuyển model sang GGUF Q8_0...")
        run(
            str(converter_python),
            str(llama_cpp / "convert_hf_to_gguf.py"),
            str(fp16_model),
            "--outfile",
            str(output),
            "--outtype",
            "q8_0",
        )

    size_gib = output.stat().st_size / (1024**3)
    print(f"Đã tạo {output} ({size_gib:.2f} GiB)")
    print("Tiếp theo: bash scripts/package_docker.sh")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", type=Path, default=ADAPTER_PATH)
    parser.add_argument("--checkpoint", help="step, ví dụ 75 hoặc checkpoint-75")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    adapter = resolve_adapter_path(args.adapter.resolve(), args.checkpoint)
    export(adapter, args.output.resolve(), args.force)


if __name__ == "__main__":
    main()
