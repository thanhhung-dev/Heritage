"""Vietnamese normalization and source-text helpers for embeddings/training."""
from __future__ import annotations

import re
import unicodedata


def nfc(text: str) -> str:
    """Wikipedia trộn cả NFC và NFD - không chuẩn hoá thì 'Huế' không khớp 'Huế'."""
    return unicodedata.normalize("NFC", text)


def strip_accents(text: str) -> str:
    """'Lăng Minh Mạng' -> 'lang minh mang'. Dùng cho nhánh index không dấu."""
    decomposed = unicodedata.normalize("NFD", nfc(text).lower())
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return plain.replace("đ", "d")


SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def sentences(text: str, min_len: int = 30) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text) if len(s.strip()) >= min_len]


def name_span(haystack_plain: str, name: str) -> tuple[int, int] | None:
    """Vị trí (đầu, cuối) của tên riêng trong text đã bỏ dấu; None nếu vắng."""
    plain = strip_accents(name).strip()
    if not plain:
        return None
    m = re.search(rf"(?<!\w){re.escape(plain)}(?!\w)", haystack_plain)
    return m.span() if m else None


def contains_name(haystack_plain: str, name: str) -> bool:
    """Khớp tên riêng theo ranh giới từ trên text đã bỏ dấu.

    Bỏ dấu hai phía để 'Ngũ Hành Sơn' trong câu hỏi khớp được với văn bản kể cả
    khi người dùng gõ 'ngu hanh son'.
    """
    return name_span(haystack_plain, name) is not None
