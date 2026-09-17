#!/usr/bin/env bash
# Train LoRA FP16/BF16 bằng Hugging Face/PEFT. Mặc định resume checkpoint mới nhất.
# Chạy trong training container, Kaggle GPU, hoặc Linux NVIDIA đã cài requirements.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python}"
CONFIG="${TRAIN_CONFIG:-training/lora_config.yaml}"

for f in data/train.jsonl data/valid.jsonl; do
  if [ ! -s "$f" ]; then
    echo "Thiếu $f. Chạy: backend/.venv/bin/python training/bootstrap_deep_qa.py"
    exit 1
  fi
done

echo "==> Config: $CONFIG"
exec "$PY" training/train_hf.py --config "$CONFIG" "$@"
