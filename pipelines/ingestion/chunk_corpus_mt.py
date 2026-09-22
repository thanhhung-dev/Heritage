#!/usr/bin/env python3
"""
Chunking corpus Đà Nẵng - Huế cho GraphRAG.
- Đọc tất cả .txt trong corpus/wiki_by_location/ (crawl theo địa điểm)
- Chia thành chunk 800 chars, overlap 100
- Lưu vào graphrag/input/ theo format GraphRAG
"""
import re
from pathlib import Path

# Đổi từ corpus/wiki/ → corpus/wiki_by_location/ (kết quả từ crawl_by_location.py)
SRC = Path("corpus/wiki_by_location")
OUT = Path("graphrag/input")
OUT.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 700
OVERLAP = 80


def chunk_text(text: str) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    text = re.sub(r"[ \t]+", " ", text)
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            # ưu tiên cắt ở dấu câu
            for sep in [". ", ".\n", "\n\n", "; "]:
                cut = text.rfind(sep, start + CHUNK_SIZE // 2, end)
                if cut > 0:
                    end = cut + len(sep)
                    break
        chunk = text[start:end].strip()
        if 200 < len(chunk) < 2000:
            chunks.append(chunk)
        start = max(end - OVERLAP, start + 1)
    return chunks


def main():
    total_chunks = 0
    files = sorted(SRC.glob("*.txt"))
    print(f"found {len(files)} source files")

    for src_file in files:
        text = src_file.read_text("utf-8")
        chunks = chunk_text(text)
        if not chunks:
            continue
        out_path = OUT / f"{src_file.stem}.txt"
        out_path.write_text("\n\n---\n\n".join(chunks), "utf-8")
        total_chunks += len(chunks)
        print(f"  {src_file.name}: {len(chunks)} chunks")

    print(f"\n✅ total: {total_chunks} chunks → {OUT}")
    print(f"   ~{total_chunks * 800 / 1_000_000:.1f} MB text")
    print(f"   ước lượng indexing: {total_chunks // 100}-{total_chunks // 50} giờ")


if __name__ == "__main__":
    main()
