"""Entity extraction retained for offline NER/training, not graph retrieval."""
from __future__ import annotations

import json
import re
from collections import Counter

from apps.backend.ai.ingestion.corpus import INDEX_FILE, usable_names
from apps.backend.common.utils.text import nfc

U = "A-ZĐÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"
L = "a-zđàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ"

CLASSIFIERS = (
    "vua", "chúa", "hoàng đế", "hoàng hậu", "công chúa", "thái tử",
    "lăng", "chùa", "đền", "miếu", "đình", "điện", "cung", "thành", "đàn", "tháp",
    "làng", "phường", "xã", "huyện", "quận", "tỉnh", "thị xã",
    "sông", "núi", "đèo", "biển", "bán đảo", "cầu", "hồ", "vịnh",
    "bảo tàng", "lễ hội", "nhà hát",
    "nhà thờ", "nhà thờ chính tòa",
    "vương triều", "triều", "nhà", "thời", "kinh thành", "hoàng thành",
)
NAME_RE = re.compile(
    r"(?<!\w)((?i:"
    + "|".join(sorted(CLASSIFIERS, key=len, reverse=True))
    + r"))[ \t]+((?:[" + U + r"][" + L + r"]+[ \t]?){1,3})"
)
YEAR_RE = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-2][0-9])(?!\d)")

MIN_ENTITY_MENTIONS = 2


def extract_names(text: str) -> Counter:
    """Trả về Counter{"lăng Tự Đức": n} - danh từ loại viết thường, tên giữ nguyên."""
    found: Counter = Counter()
    for cls, name in NAME_RE.findall(nfc(text)):
        name = name.strip()
        if len(name) >= 2:
            found[f"{cls.lower()} {name}"] += 1
    return found


def extract_years(text: str) -> Counter:
    return Counter(YEAR_RE.findall(text))


def curated_entities() -> list[dict]:
    """Training labels from usable crawled documents and uncrawled locations."""
    usable = usable_names()
    data = json.loads(INDEX_FILE.read_text("utf-8"))
    return [
        {"name": e["name"], "region": e.get("region", ""), "category": e.get("category", "")}
        for e in (
            [e for e in data.get("success", []) if e["name"] in usable]
            + list(data.get("failed", []))
        )
    ]
