#!/usr/bin/env bash
# Merge PEFT adapter rồi xuất GGUF Q8_0 cho llama.cpp.
#   bash training/fuse.sh       # adapter tốt nhất
#   bash training/fuse.sh 75    # checkpoint-75
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python}"
CKPT="${1:-}"
ARGS=(--adapter "${ADAPTER:-models/peft-adapter}" --output "${OUTPUT:-models/qwen-fused.gguf}")
[ -z "$CKPT" ] || ARGS+=(--checkpoint "$CKPT")
exec "$PY" scripts/export_gguf.py "${ARGS[@]}"
