#!/usr/bin/env bash
# Chọn PEFT checkpoint để đánh giá/xuất model. Trainer đã tự lưu best model ở root,
# nên script này chỉ cần khi muốn quảng bá một checkpoint cụ thể.
#
#   bash training/select_adapter.sh 75
#   bash training/select_adapter.sh       # best model ở root
set -euo pipefail
cd "$(dirname "$0")/.."

ADAPTER=./models/peft-adapter
SERVE=./models/peft-serve
CKPT="${1:-}"

if [ -n "$CKPT" ]; then
  CKPT="${CKPT#checkpoint-}"
  SRC="$ADAPTER/checkpoint-$CKPT"
  if [ ! -f "$SRC/adapter_model.safetensors" ]; then
    echo "Không có $SRC. Các checkpoint hiện có:"
    find "$ADAPTER" -maxdepth 1 -type d -name 'checkpoint-*' -print
    exit 1
  fi
  LABEL="checkpoint-$CKPT"
else
  SRC="$ADAPTER"
  [ -f "$SRC/adapter_model.safetensors" ] || { echo "Không có adapter trong $SRC"; exit 1; }
  LABEL="best"
fi

mkdir -p "$SERVE"
find "$SERVE" -maxdepth 1 -type f -delete
find "$SRC" -maxdepth 1 -type f -exec cp {} "$SERVE/" \;
echo "$LABEL" > "$SERVE/CHECKPOINT"

echo "==> models/peft-serve/ = $LABEL"
echo "    Xuất: python scripts/export_gguf.py --adapter models/peft-serve"
