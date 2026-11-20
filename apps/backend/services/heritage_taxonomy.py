"""Stable editorial taxonomy; independent of homepage labels and RAG entities."""
from dataclasses import dataclass

ENTITY_TYPES = frozenset({"place", "artifact", "collection", "event", "person", "practice"})


@dataclass(frozen=True)
class Category:
    key: str
    name_vi: str
    name_en: str
    entity_types: frozenset[str]


def category(key, vi, en, *kinds):
    return Category(key, vi, en, frozenset(kinds))


CATEGORIES = (
    category("historical_site", "Di tích lịch sử", "Historical site", "place"),
    category("architecture", "Công trình kiến trúc", "Architecture", "place"),
    category("scenic_landscape", "Danh lam thắng cảnh", "Scenic landscape", "place"),
    category("religious_site", "Di tích tôn giáo, tín ngưỡng", "Religious site", "place"),
    category("museum", "Bảo tàng", "Museum", "place"),
    category("artifact", "Cổ vật và hiện vật", "Artifacts", "artifact", "collection"),
    category("festival", "Lễ hội", "Festival", "event"),
    category("ritual", "Nghi lễ", "Ritual", "event", "practice"),
    category("intangible_heritage", "Di sản văn hóa phi vật thể", "Intangible heritage", "practice"),
    category("historical_figure", "Nhân vật lịch sử", "Historical figure", "person"),
    category("artisan", "Nghệ nhân", "Artisan", "person"),
    category("community_tradition", "Phong tục, truyền thống", "Community tradition", "practice", "place"),
    category("traditional_craft", "Nghề thủ công truyền thống", "Traditional craft", "practice"),
    category("cultural_experience", "Trải nghiệm văn hóa", "Cultural experience", "practice", "place"),
)
BY_KEY = {item.key: item for item in CATEGORIES}


def validate_categories(entity_type: str, keys: list[str], primary: str):
    if entity_type not in ENTITY_TYPES or not keys or len(keys) != len(set(keys)) or primary not in keys:
        raise ValueError("Supply a valid entity type, unique categories and one primary category")
    if any(key not in BY_KEY or entity_type not in BY_KEY[key].entity_types for key in keys):
        raise ValueError("Category is incompatible with this entity type")
    # A communal building needs explicit evidence, checked by the engine/admin.
    return keys
