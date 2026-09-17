#!/usr/bin/env bash
# Sinh thử qua llama.cpp server để xem GGUF đã học đúng định dạng chưa.
#   bash training/generate.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-backend/.venv/bin/python}"
PROMPT_FILE="${PROMPT_FILE:-./prompts/test_quick.txt}"
MAX_TOKENS="${MAX_TOKENS:-400}"

[ -f "$PROMPT_FILE" ] || { echo "Không có $PROMPT_FILE"; exit 1; }

i=0
while IFS= read -r -d '' block; do
  i=$((i + 1))
  echo "======================== PROMPT $i ========================"
  printf '%s\n\n' "$block"
  "$PY" scripts/try_prompt.py "$block" --source "" --max-tokens "$MAX_TOKENS"
  echo ""
done < <($PY -c '
import sys
text = open(sys.argv[1], encoding="utf-8").read()
for block in text.split("\n---\n"):
    block = block.strip()
    if block:
        sys.stdout.write(block + "\0")
' "$PROMPT_FILE")
