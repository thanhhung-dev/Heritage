"""Chunk text for R2 ingestion and load the offline Wikipedia training corpus.

Serving reads indexed chunks from OpenSearch; it does not load local corpus files.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from pathlib import Path

from apps.backend.core.config import PROJECT_ROOT

CORPUS_DIR = PROJECT_ROOT / "corpus" / "wiki_by_location"
INDEX_FILE = PROJECT_ROOT / "corpus" / "locations_index.json"

# 800, không phải 1000: bài "Cao lầu" sau khi cắt phần tham khảo còn 973 ký tự -
# một bài THẬT, 4 đoạn văn liền mạch, nhưng ngưỡng 1000 loại nó khỏi corpus và
# câu "cao lầu là món gì" khi đó bị trả về chunk của Lăng Minh Mạng. Trang định
# hướng (Đàn Nam Giao, 205 ký tự, chỉ là danh sách liên kết) vẫn bị loại.
MIN_DOC_CHARS = 800
MAX_CHUNK_CHARS = 1200
MIN_CHUNK_CHARS = 200

# Các mục cuối bài chỉ chứa điều hướng/tham khảo, không phải nội dung
STOP_SECTIONS = {
    "xem thêm", "tham khảo", "chú thích", "liên kết ngoài", "hình ảnh",
    "thể loại", "ghi chú", "đọc thêm", "thư mục", "chú giải", "tài liệu",
}


def wiki_url(title: str) -> str:
    return "https://vi.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))


def clean_wiki_text(text: str) -> str:
    """Cắt bỏ phần điều hướng/tham khảo ở cuối bài."""
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.lower().rstrip(":") in STOP_SECTIONS:
            break
        kept.append(line)
    return "\n".join(kept).strip()


def is_usable(text: str) -> bool:
    """Bỏ tài liệu quá ngắn và trang định hướng (phần lớn là dòng ngắn)."""
    if len(text) < MIN_DOC_CHARS:
        return False
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return False
    short = sum(1 for l in lines if len(l) < 60)
    return short / len(lines) <= 0.8


def is_heading(line: str) -> bool:
    """wikipediaapi đặt mỗi đoạn trên 1 dòng, tiêu đề mục là dòng ngắn không dấu câu."""
    if len(line) > 60 or line.endswith((".", ",", ";", ":", "?", "!")):
        return False
    return len(line.split()) <= 8


def split_sections(text: str) -> list[tuple[str, str]]:
    """Tách bài thành [(tiêu đề mục, nội dung)]; mục đầu là phần mở đầu."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if is_heading(line):
            sections.append((line, []))
        else:
            sections[-1][1].append(line)
    return [(h, " ".join(b).strip()) for h, b in sections if " ".join(b).strip()]


def split_by_size(text: str, size: int) -> list[str]:
    """Cắt theo ranh giới câu, mỗi phần <= size ký tự."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    out: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(". ", start + size // 2, end)
            if cut > 0:
                end = cut + 2
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        start = end
    return out


def chunk_document(text: str) -> list[dict]:
    """Chunk giữ tiêu đề mục làm context - dùng để chấm điểm liên quan."""
    chunks: list[dict] = []
    buf_heads: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        body = " ".join(buf).strip()
        if len(body) >= MIN_CHUNK_CHARS:
            heads = [h for h in dict.fromkeys(buf_heads) if h]
            chunks.append({"heading": " / ".join(heads), "text": body})
        buf_heads.clear()
        buf.clear()

    for heading, body in split_sections(text):
        for piece in split_by_size(body, MAX_CHUNK_CHARS):
            if buf and sum(len(x) for x in buf) + len(piece) > MAX_CHUNK_CHARS:
                flush()
            buf_heads.append(heading)
            buf.append(piece)
            if sum(len(x) for x in buf) >= int(MAX_CHUNK_CHARS * 0.7):
                flush()
    flush()
    return chunks


def chunk_text_spans(
    text: str, max_chars: int = 2400, overlap_chars: int = 300,
) -> list[dict]:
    """Chunk extracted text without losing headings or exact source offsets.

    Prefer paragraph, sentence, then word boundaries. Character limits are not
    token limits; runtime must still enforce the model's token budget.
    """
    if max_chars < 32 or not 0 <= overlap_chars < max_chars // 2:
        raise ValueError("max_chars >= 32; 0 <= overlap_chars < max_chars / 2")
    chunks: list[dict] = []
    start = 0
    while start < len(text):
        limit = min(start + max_chars, len(text))
        end = limit
        if limit < len(text):
            window = text[start + max_chars // 2:limit]
            for pattern in (r"\n\s*\n", r"[.!?][\s]+", r"\s+"):
                boundaries = list(re.finditer(pattern, window))
                if boundaries:
                    end = start + max_chars // 2 + boundaries[-1].end()
                    break
        while start < end and text[start].isspace():
            start += 1
        trimmed_end = end
        while trimmed_end > start and text[trimmed_end - 1].isspace():
            trimmed_end -= 1
        if trimmed_end > start:
            chunks.append({"text": text[start:trimmed_end],
                           "char_start": start, "char_end": trimmed_end})
        if end == len(text):
            break
        next_start = max(start + 1, end - overlap_chars)
        # Start overlap at a word boundary without leaving a coverage gap.
        if overlap_chars:
            boundary = next_start
            while boundary < end and not text[boundary - 1].isspace():
                boundary += 1
            if boundary < end:
                next_start = boundary
        start = next_start
    return chunks


def load_docs() -> tuple[list[dict], list[tuple[str, str]]]:
    """Đọc corpus đã crawl -> [{name, category, region, url, chunks}], + lý do bỏ.

    Bỏ: thiếu file, quá ngắn / trang định hướng, trùng nội dung (redirect wiki
    làm hai tên trỏ về cùng một bài, ví dụ Bánh khoái / Bánh xèo).
    """
    data = json.loads(INDEX_FILE.read_text("utf-8"))
    docs: list[dict] = []
    skipped: list[tuple[str, str]] = []
    seen: dict[str, str] = {}

    for loc in sorted(data["success"], key=lambda x: x["name"]):
        path = CORPUS_DIR / loc["file"]
        if not path.exists():
            skipped.append((loc["name"], "thiếu file corpus"))
            continue
        text = clean_wiki_text(path.read_text("utf-8"))
        if not is_usable(text):
            skipped.append((loc["name"], f"quá ngắn / trang định hướng ({len(text)} ký tự)"))
            continue
        digest = hashlib.md5(text.encode("utf-8")).hexdigest()
        if digest in seen:
            skipped.append((loc["name"], f"trùng nội dung với '{seen[digest]}'"))
            continue
        seen[digest] = loc["name"]
        chunks = chunk_document(text)
        if not chunks:
            skipped.append((loc["name"], "không tạo được chunk"))
            continue
        docs.append({
            "name": loc["name"],
            "category": loc.get("category", ""),
            "region": loc.get("region", ""),
            "url": loc.get("url") or wiki_url(loc["name"]),
            "chunks": chunks,
        })
    return docs, skipped


def usable_names() -> set[str]:
    docs, _ = load_docs()
    return {d["name"] for d in docs}
