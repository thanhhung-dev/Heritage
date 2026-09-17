#!/usr/bin/env python3
"""Fine-tune a chat model with portable Hugging Face LoRA.

Heavy ML dependencies are imported only by ``main`` so configuration and
tokenization contracts can be tested without a CUDA environment.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PATH_KEYS = ("train_file", "valid_file", "output_dir")


def load_config(path: Path) -> dict[str, Any]:
    """Load training YAML and resolve data/output paths from the project root."""
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"Config phải là YAML object: {path}")
    required = ("model_id", *PATH_KEYS)
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"Config thiếu: {', '.join(missing)}")
    for key in PATH_KEYS:
        value = Path(config[key])
        config[key] = value if value.is_absolute() else ROOT / value
    return config


def find_last_checkpoint(output_dir: Path) -> Path | None:
    """Return the checkpoint directory with the greatest numeric step."""
    checkpoints: list[tuple[int, Path]] = []
    if output_dir.is_dir():
        for path in output_dir.glob("checkpoint-*"):
            try:
                checkpoints.append((int(path.name.removeprefix("checkpoint-")), path))
            except ValueError:
                continue
    return max(checkpoints, default=(0, None), key=lambda item: item[0])[1]


def tokenize_conversation(
    tokenizer: Any,
    messages: list[dict[str, str]],
    max_seq_length: int,
    enable_thinking: bool = False,
) -> dict[str, list[int]]:
    """Tokenize one chat and calculate loss only on assistant tokens."""
    if not messages or messages[-1].get("role") != "assistant":
        raise ValueError("Mẫu phải kết thúc bằng một message assistant")
    prompt = tokenizer.apply_chat_template(
        messages[:-1],
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        truncation=True,
        max_length=max_seq_length,
        enable_thinking=enable_thinking,
    )
    encoded = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=False,
        return_dict=True,
        truncation=True,
        max_length=max_seq_length,
        enable_thinking=enable_thinking,
    )
    prompt_ids = list(prompt["input_ids"])
    input_ids = list(encoded["input_ids"])
    if input_ids[: len(prompt_ids)] != prompt_ids:
        raise ValueError(
            "Chat template không tạo generation prompt trùng prefix của hội thoại"
        )
    labels = [-100] * len(prompt_ids) + input_ids[len(prompt_ids):]
    if all(label == -100 for label in labels):
        raise ValueError("Mẫu không còn token assistant sau khi tokenize/truncate")
    return {
        "input_ids": input_ids,
        "attention_mask": list(encoded["attention_mask"]),
        "labels": labels,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            messages = row.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ValueError(f"{path}:{line_number} thiếu messages")
            rows.append(row)
    if not rows:
        raise ValueError(f"Dataset rỗng: {path}")
    return rows


def _dtype(torch: Any, value: str) -> Any:
    if value == "auto":
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    try:
        return getattr(torch, value)
    except AttributeError as exc:
        raise ValueError(f"compute_dtype không hợp lệ: {value}") from exc


def train(config: dict[str, Any], fresh: bool) -> None:
    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    if not torch.cuda.is_available():
        raise RuntimeError(
            "LoRA trainer cần NVIDIA CUDA. Trên Mac hãy chạy smoke/unit test; "
            "train thật bằng Docker trên Linux NVIDIA hoặc Kaggle GPU."
        )

    seed = int(config.get("seed", 42))
    random.seed(seed)
    set_seed(seed)

    model_id = str(config["model_id"])
    max_seq_length = int(config.get("max_seq_length", 1536))
    trust_remote_code = bool(config.get("trust_remote_code", False))
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=trust_remote_code,
        use_fast=True,
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    def encode(row: dict[str, Any]) -> dict[str, list[int]]:
        return tokenize_conversation(
            tokenizer,
            row["messages"],
            max_seq_length,
            enable_thinking=bool(config.get("enable_thinking", False)),
        )

    train_dataset = Dataset.from_list(read_jsonl(config["train_file"])).map(
        encode, remove_columns=["messages"], desc="Tokenize train"
    )
    valid_dataset = Dataset.from_list(read_jsonl(config["valid_file"])).map(
        encode, remove_columns=["messages"], desc="Tokenize valid"
    )

    compute_dtype = _dtype(torch, str(config.get("compute_dtype", "auto")))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=compute_dtype,
        device_map={"": local_rank},
        low_cpu_mem_usage=True,
        trust_remote_code=trust_remote_code,
    )
    model.config.use_cache = False
    model = get_peft_model(
        model,
        LoraConfig(
            r=int(config.get("lora_rank", 16)),
            lora_alpha=int(config.get("lora_alpha", 32)),
            lora_dropout=float(config.get("lora_dropout", 0.05)),
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=config.get("target_modules", "all-linear"),
        ),
    )
    if bool(config.get("gradient_checkpointing", True)):
        model.enable_input_require_grads()
    model.print_trainable_parameters()

    output_dir: Path = config["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    use_bf16 = compute_dtype == torch.bfloat16
    arguments = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=float(config.get("num_train_epochs", 3)),
        per_device_train_batch_size=int(config.get("batch_size", 1)),
        per_device_eval_batch_size=int(config.get("eval_batch_size", 1)),
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 8)),
        learning_rate=float(config.get("learning_rate", 1e-4)),
        lr_scheduler_type=str(config.get("lr_scheduler_type", "cosine")),
        warmup_ratio=float(config.get("warmup_ratio", 0.08)),
        weight_decay=float(config.get("weight_decay", 0.0)),
        max_grad_norm=float(config.get("max_grad_norm", 1.0)),
        logging_steps=int(config.get("logging_steps", 10)),
        eval_strategy="steps",
        eval_steps=int(config.get("eval_steps", 25)),
        save_strategy="steps",
        save_steps=int(config.get("save_steps", 25)),
        save_total_limit=int(config.get("save_total_limit", 3)),
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        gradient_checkpointing=bool(config.get("gradient_checkpointing", True)),
        fp16=not use_bf16,
        bf16=use_bf16,
        optim=str(config.get("optimizer", "adamw_torch")),
        report_to=str(config.get("report_to", "none")),
        seed=seed,
        data_seed=seed,
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=arguments,
        train_dataset=train_dataset,
        eval_dataset=valid_dataset,
        data_collator=DataCollatorForSeq2Seq(
            tokenizer=tokenizer,
            padding=True,
            label_pad_token_id=-100,
            pad_to_multiple_of=8,
        ),
        processing_class=tokenizer,
    )

    checkpoint = None if fresh else find_last_checkpoint(output_dir)
    if checkpoint:
        print(f"Resume từ {checkpoint}")
    trainer.train(resume_from_checkpoint=str(checkpoint) if checkpoint else None)
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(output_dir)
    metrics = trainer.evaluate()
    (output_dir / "eval_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Adapter PEFT tốt nhất: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "training" / "lora_config.yaml")
    parser.add_argument("--fresh", action="store_true", help="không resume checkpoint")
    args = parser.parse_args()
    train(load_config(args.config), fresh=args.fresh)


if __name__ == "__main__":
    main()
