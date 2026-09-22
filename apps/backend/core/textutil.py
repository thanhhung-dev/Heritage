"""Chuẩn hoá & tách token tiếng Việt cho retrieval.

Không dùng thư viện tách từ ngoài (underthesea/pyvi): corpus nhỏ, và BM25 theo
âm tiết + BM25 theo n-gram ký tự đã đủ mạnh. Quan trọng hơn là xử lý được truy
vấn KHÔNG DẤU ("lang minh mang") - người chat gõ không dấu rất thường xuyên,
và đó là trường hợp mà mọi retrieval chỉ-có-dấu đều trả về rỗng.
"""
from __future__ import annotations

import re
import unicodedata

WORD_RE = re.compile(r"\w+", re.UNICODE)

NGRAM_SIZE = 4

STOPWORDS = frozenset("""
là của và có các một những được trong cho với khi đã này đó thì mà ở từ đến về
ra vào như cũng nên hay hoặc bởi vì do tại trên dưới sau trước còn rất nhiều
nào gì ai đâu sao thế hãy cùng theo để không chưa sẽ đang bị nhưng nếu tuy
""".split())


def nfc(text: str) -> str:
    """Wikipedia trộn cả NFC và NFD - không chuẩn hoá thì 'Huế' không khớp 'Huế'."""
    return unicodedata.normalize("NFC", text)


def strip_accents(text: str) -> str:
    """'Lăng Minh Mạng' -> 'lang minh mang'. Dùng cho nhánh index không dấu."""
    decomposed = unicodedata.normalize("NFD", nfc(text).lower())
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return plain.replace("đ", "d")


def word_tokens(text: str) -> list[str]:
    """Token có dấu, đã bỏ hư từ. Nhánh chính xác về chính tả."""
    return [t for t in WORD_RE.findall(nfc(text).lower()) if t not in STOPWORDS]


def ngram_tokens(text: str, size: int = NGRAM_SIZE) -> list[str]:
    """N-gram ký tự trên text KHÔNG DẤU.

    Bắt được: truy vấn không dấu, sai chính tả, và biến thể ghép từ
    ('Thiên Mụ' / 'chùa Thiên Mụ tự') - những chỗ token theo từ trượt.
    """
    flat = re.sub(r"\s+", " ", strip_accents(text)).strip()
    if len(flat) <= size:
        return [flat] if flat else []
    return [flat[i : i + size] for i in range(len(flat) - size + 1)]


SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def sentences(text: str, min_len: int = 30) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text) if len(s.strip()) >= min_len]


def name_span(haystack_plain: str, name: str) -> tuple[int, int] | None:
    """Vị trí (đầu, cuối) của tên riêng trong text đã bỏ dấu; None nếu vắng.

    Cần VỊ TRÍ chứ không chỉ có/không: câu "Lăng Tự Đức ở phường Ngũ Hành Sơn
    đúng không" nêu HAI tên, và thứ tự xuất hiện là thứ phân biệt CHỦ ĐỀ với
    GIẢ ĐỊNH - xem `subject_and_claims` trong retriever.py.
    """
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
