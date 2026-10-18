"""Gán nhãn NER bằng CHÍNH graph deterministic - không cần gán nhãn tay.

Vì sao làm được: kg.py đã trích entity bằng mẫu "danh từ loại + tên riêng" của
tiếng Việt ("lăng Tự Đức", "vua Minh Mạng") cộng danh sách địa điểm curated và
mốc năm. Danh từ loại đã cho biết LOẠI của entity, nên chỉ cần map danh từ loại
-> 1 trong 4 loại NER là có nhãn vàng. Mọi nhãn vì thế truy được về một chuỗi
có thật trong văn bản, giống hệt nguyên tắc của graph.

Dùng ở hai chỗ: sinh mẫu NER cho training data, và điền sẵn phần NER của gold set.
"""
from __future__ import annotations

import re as _RE
from functools import lru_cache

from apps.backend.core.kg import (
    CLASSIFIERS,
    MIN_ENTITY_MENTIONS,
    curated_entities,
    extract_names,
    extract_years,
)
from apps.backend.core.prompt import NER_TYPES
from apps.backend.core.textutil import nfc, strip_accents

# Danh từ loại -> loại NER. Triều đại ("triều Nguyễn", "thời Minh Mạng") xếp vào
# "thời gian": trong văn bản di sản chúng luôn là mốc thời gian, không phải nơi.
TYPE_BY_CLASSIFIER: dict[str, str] = {
    "vua": "người", "chúa": "người", "hoàng đế": "người", "hoàng hậu": "người",
    "công chúa": "người", "thái tử": "người",

    "lăng": "địa điểm", "chùa": "địa điểm", "đền": "địa điểm", "miếu": "địa điểm",
    "đình": "địa điểm", "điện": "địa điểm", "cung": "địa điểm", "thành": "địa điểm",
    "đàn": "địa điểm", "làng": "địa điểm", "phường": "địa điểm", "xã": "địa điểm",
    "huyện": "địa điểm", "quận": "địa điểm", "tỉnh": "địa điểm", "thị xã": "địa điểm",
    "sông": "địa điểm", "núi": "địa điểm", "đèo": "địa điểm", "biển": "địa điểm",
    "bán đảo": "địa điểm", "cầu": "địa điểm", "hồ": "địa điểm", "vịnh": "địa điểm",
    "bảo tàng": "địa điểm", "nhà hát": "địa điểm",
    "kinh thành": "địa điểm", "hoàng thành": "địa điểm",
    "nhà thờ": "địa điểm", "nhà thờ chính tòa": "địa điểm",

    "lễ hội": "sự kiện",

    "vương triều": "thời gian", "triều": "thời gian", "nhà": "thời gian",
    "thời": "thời gian",
}

# Thêm danh từ loại vào kg.py mà quên map ở đây thì entity loại đó KHÔNG được gán
# nhãn - gold set sai một cách âm thầm và F1 đo ra vô nghĩa. Fail ngay lúc import.
_UNMAPPED = set(CLASSIFIERS) - set(TYPE_BY_CLASSIFIER)
if _UNMAPPED:
    raise RuntimeError(
        f"kg.CLASSIFIERS có {sorted(_UNMAPPED)} chưa được map sang loại NER trong "
        f"{__name__}.TYPE_BY_CLASSIFIER"
    )

# Địa điểm curated: loại suy ra từ category trong locations_index.json.
# "Ẩm thực" và "Nghệ thuật" không thuộc 4 loại nào (món ăn, loại hình nghệ thuật
# không phải người/nơi/sự kiện/thời gian) nên bỏ, không gán bừa.
TYPE_BY_CATEGORY: dict[str, str] = {
    "Di tích lịch sử": "địa điểm",
    "Danh thắng": "địa điểm",
    "Làng nghề": "địa điểm",
    "Lễ hội": "sự kiện",
}

_CLS_BY_LEN = sorted(CLASSIFIERS, key=len, reverse=True)

# Từ ghép mà chữ thứ hai cũng là một danh từ loại: "cung đình", "cung điện",
# "nhà thờ", "đình làng". Trong các cụm này, phần sau KHÔNG mở đầu một tên riêng.
COMPOUNDS = frozenset({("cung", "đình"), ("cung", "điện"), ("nhà", "thờ"), ("đình", "làng")})

# Hai danh từ loại này còn là từ thông dụng, regex của kg.py không phân biệt được:
#   "đổi tên núi Châu Chữ ... thành Ứng Sơn"  -> "thành" là ĐỘNG TỪ, không phải toà thành
#   "2 nhà Tả, Hữu tòng tự"                   -> "nhà" là căn nhà, không phải triều đại
# Nên chúng phải qua thêm một cửa thay vì tin regex.
DYNASTIES = frozenset(
    strip_accents(x) for x in (
        "Nguyễn", "Lê", "Trần", "Lý", "Hồ", "Mạc", "Đinh", "Ngô", "Trịnh",
        "Tây Sơn", "Hậu Lê", "Tiền Lê", "Hậu Lý", "Tiền Lý", "Hùng", "Thục",
        "Triệu", "Tần", "Hán", "Đường", "Minh", "Thanh",
    )
)
AMBIGUOUS = ("thành", "nhà")


def _plausible(name: str, cls: str, allowed: set[str] | None) -> bool:
    """Cửa phụ cho danh từ loại nhập nhằng. Các loại còn lại đi thẳng."""
    if cls == "nhà":
        # "nhà Nguyễn" đúng, "nhà Tả" thì không - triều đại Việt Nam là tập ĐÓNG.
        return strip_accents(name[len(cls):].strip()) in DYNASTIES
    if cls == "thành":
        # Không có danh sách đóng cho toà thành, nên đòi tên được nhắc lại trong
        # cả bài: "thành Ứng Sơn" do đọc sai chỉ xuất hiện đúng một lần.
        return allowed is None or name in allowed
    return True


def classifier_of(name: str) -> str:
    """'lăng Tự Đức' -> 'lăng'. Dài nhất trước để 'hoàng thành' thắng 'thành'."""
    low = name.lower()
    for cls in _CLS_BY_LEN:
        if low.startswith(cls + " "):
            return cls
    return ""


@lru_cache(maxsize=1)
def _curated_typed() -> tuple[tuple[str, str], ...]:
    return tuple(
        (e["name"], TYPE_BY_CATEGORY[e["category"]])
        for e in curated_entities()
        if e["category"] in TYPE_BY_CATEGORY
    )


def allowed_names(doc_text: str) -> set[str]:
    """Tên đạt ngưỡng nhắc lại trong CẢ bài.

    Cùng ngưỡng MIN_ENTITY_MENTIONS mà kg.py dùng khi dựng graph. Chỉ còn dùng cho
    danh từ loại nhập nhằng ("thành") trong _plausible(); KHÔNG lọc toàn bộ nhãn
    nữa - xem lý do ở docstring của ner_label().
    """
    return {n for n, c in extract_names(doc_text).items() if c >= MIN_ENTITY_MENTIONS}


def _dedupe(names: list[str]) -> list[str]:
    """Bỏ trùng không phân biệt hoa/thường, và bỏ tên bị BAO trong tên dài hơn.

    'thành Huế' nằm trong 'kinh thành Huế' -> chỉ giữ tên dài, nếu không thì cùng
    một thực thể bị tính hai lần và precision của model bị trừ oan.
    """
    kept: list[str] = []
    for name in sorted(set(names), key=len, reverse=True):
        plain = strip_accents(name)
        if any(plain in strip_accents(k) for k in kept):
            continue
        kept.append(name)
    return sorted(kept, key=str.lower)


def _standalone(text_nfc: str, text_plain: str, name: str, cls: str) -> bool:
    """False nếu MỌI lần xuất hiện của `name` đều là ĐUÔI của một từ ghép.

    'Nhã nhạc cung đình Huế' làm regex của kg.py sinh ra 'đình Huế' (23 lần trong
    corpus) - nó chỉ là đuôi của cụm 'cung đình', không phải một địa điểm. Regex
    kia không thấy được vì nó chỉ nhìn về phía sau danh từ loại.

    Chỉ chặn theo DANH SÁCH TỪ GHÉP đóng, không chặn mọi danh từ loại đứng trước:
    "thời vua Minh Mạng", "lăng vua Gia Long", "hội điện Hòn Chén" đều là entity
    thật, chặn hết thì mất ~77 nhãn đúng để tránh 23 nhãn sai.

    So sánh trên bản CÓ DẤU: "cùng điện Long An" (cùng = và) từng bị nhận thành
    "cung điện" vì bỏ dấu làm hai từ giống nhau.
    """
    plain = strip_accents(name)
    for m in _RE.finditer(rf"(?<!\w){_RE.escape(plain)}(?!\w)", text_plain):
        before = text_nfc[: m.start()].rstrip().split()
        prev = before[-1].lower() if before else ""
        if (prev, cls) not in COMPOUNDS:
            return True
    return False


def _surface(text_nfc: str, text_plain: str, name: str) -> str | None:
    """Dạng chữ ĐÚNG NHƯ TRONG VĂN BẢN của `name` ('Lăng Khải Định' -> 'lăng Khải Định').

    Tên curated lấy từ locations_index.json viết hoa theo tên bài Wikipedia, còn
    trong câu thường viết thường. Nhãn vàng phải là chuỗi có thật trong đoạn -
    đúng nguyên tắc mà cả graph lẫn báo cáo đều dựa vào - nên trả về đoạn cắt từ
    văn bản. strip_accents giữ nguyên độ dài nên chỉ số hai bên khớp nhau.
    """
    plain = strip_accents(name).strip()
    if not plain:
        return None
    m = _RE.search(rf"(?<!\w){_RE.escape(plain)}(?!\w)", text_plain)
    return text_nfc[m.start(): m.end()] if m else None


def ner_label(text: str, allowed: set[str] | None = None) -> dict[str, list[str]]:
    """Nhãn NER của một đoạn text. Luôn trả về đủ 4 khóa, theo thứ tự NER_TYPES.

    `allowed` KHÔNG dùng để lọc tên nữa. Lọc theo ngưỡng nhắc lại của cả bài làm
    nhãn vàng thiếu những entity chỉ được nhắc một lần ("phường Thủy Xuân",
    "điện Kiến Trung", "hoàng đế Thiệu Trị") - model trích đúng lại bị trừ điểm,
    và trong câu liệt kê thì nhãn chỉ có 2/4 cái lăng, tức là dạy model bỏ sót.
    Nó chỉ còn là cửa phụ cho danh từ loại nhập nhằng, xem _plausible().
    """
    buckets: dict[str, list[str]] = {t: [] for t in NER_TYPES}
    text = nfc(text)
    plain = strip_accents(text)

    for name in extract_names(text):
        cls = classifier_of(name)
        ner_type = TYPE_BY_CLASSIFIER.get(cls)
        if not ner_type or not _standalone(text, plain, name, cls):
            continue
        if not _plausible(name, cls, allowed):
            continue
        buckets[ner_type].append(name)

    for name, ner_type in _curated_typed():
        surface = _surface(text, plain, name)
        if surface:
            buckets[ner_type].append(surface)

    buckets["thời gian"].extend(extract_years(text))

    return {t: _dedupe(buckets[t]) for t in NER_TYPES}


def n_labels(label: dict[str, list[str]]) -> int:
    return sum(len(v) for v in label.values())
