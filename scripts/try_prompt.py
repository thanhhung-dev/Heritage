#!/usr/bin/env python3
"""Thử prompt trên GGUF đang chạy bằng llama.cpp server.

Dùng đúng SYSTEM + chat template của backend/core/prompt.py - cùng thứ mà
bootstrap_deep_qa.py sinh data và score_gold.py đo.

  # Hỏi qua retrieval thật (giống lúc chạy app)
  backend/.venv/bin/python scripts/try_prompt.py "Hãy kể về Lăng Gia Long"

  # Tự đưa nguồn, bỏ qua retrieval
  backend/.venv/bin/python scripts/try_prompt.py "Đèo Hải Vân cao bao nhiêu?" --source "..."

  # Test từ chối: không nguồn -> phải từ chối
  backend/.venv/bin/python scripts/try_prompt.py "Chùa Một Cột xây năm nào?" --source ""

  # Test NER
  backend/.venv/bin/python scripts/try_prompt.py --ner "Điện Hòn Chén được vua Minh Mạng cho tu sửa vào tháng 3/1832."

Trước khi chạy, khởi động service `llm` bằng Docker Compose hoặc đặt
LLAMA_SERVER_URL tới một OpenAI-compatible server.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.core.llm import _llama_server_generate  # noqa: E402
from backend.core.prompt import NER_QUESTION, chat_messages  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--source", default=None,
                    help='Nguồn đưa tay. Bỏ trống ("") để test từ chối. '
                         "Không truyền -> lấy bằng retrieval thật.")
    ap.add_argument("--ner", action="store_true",
                    help="Coi question là đoạn văn cần trích entity")
    ap.add_argument("--max-tokens", type=int, default=768)
    args = ap.parse_args()

    if args.ner:
        source, question = "", NER_QUESTION.format(text=args.question)
    elif args.source is not None:
        source, question = args.source, args.question
    else:
        from backend.core.rag import retrieve_context
        question = args.question
        source, hits = retrieve_context(args.question)
        print(f"--- retrieval: {len(hits)} đoạn, {len(source)} ký tự", file=sys.stderr)
        for h in hits:
            print(f"      {h.get('doc') or h.get('name', '?')}", file=sys.stderr)
        if not source:
            print("--- retrieval không trả về nguồn -> model PHẢI từ chối", file=sys.stderr)

    out = _llama_server_generate(
        chat_messages(source, question), max_tokens=args.max_tokens
    )
    print("\n" + out.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
