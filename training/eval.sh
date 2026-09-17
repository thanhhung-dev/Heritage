#!/usr/bin/env bash
# Đánh giá NER/citation/refusal trên gold set bằng Transformers + PEFT.
#   bash training/eval.sh          # adapter tốt nhất được trainer lưu ở output_dir
#   bash training/eval.sh 75       # checkpoint-75
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python}"
CKPT="${1:-}"
OUT="${OUT:-eval/report_peft${CKPT:+_ck${CKPT}}.json}"
ARGS=(--gold eval/gold.jsonl --out "$OUT")
[ -z "$CKPT" ] || ARGS+=(--checkpoint "$CKPT")
exec "$PY" training/score_gold.py "${ARGS[@]}"
