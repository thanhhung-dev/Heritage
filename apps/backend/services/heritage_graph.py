"""In-process heritage-complex graph for related follow-up entities."""
from __future__ import annotations

from functools import lru_cache

import networkx as nx

from apps.backend.services.tour_scope import AREAS, allowed_output, normalized

# Interior names already used by the product. Hubs come from the tour registry,
# so a new area is a graph node without editing this list.
_PARTS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("lang-tu-duc", "bi-dinh", "Bi Đình", ("Bi Đình", "Bi Dinh")),
    ("lang-tu-duc", "hoa-khiem", "Điện Hòa Khiêm", ("Điện Hòa Khiêm", "Hòa Khiêm Điện", "Hòa Khiêm")),
    ("lang-tu-duc", "mo-tu-duc", "khu mộ vua Tự Đức", ("khu mộ vua Tự Đức", "mộ vua Tự Đức", "khu mộ")),
    ("chua-thien-mu", "thap-phuoc-duyen", "Tháp Phước Duyên", ("Tháp Phước Duyên",)),
)


@lru_cache(maxsize=1)
def heritage_graph() -> nx.Graph:
    graph = nx.Graph()
    for area in AREAS:
        graph.add_node(area.id, title=area.title, aliases=(area.id, *area.slugs, *area.names), kind="area")
    for area_id, part_id, part_title, part_aliases in _PARTS:
        if area_id not in graph:
            continue
        graph.add_node(part_id, title=part_title, aliases=part_aliases, kind="part")
        graph.add_edge(area_id, part_id, kind="contains")
    return graph


def _area_ids() -> set[str]:
    return {node for node, data in heritage_graph().nodes(data=True) if data.get("kind") == "area"}


def _host_title(asked: str, area_title: str | None) -> str:
    if area_title and area_title.strip():
        return area_title.split("(", 1)[0].strip()
    graph = heritage_graph()
    matched = _matched_nodes(asked)
    hubs = [node for node in matched if node in _area_ids()]
    if len(hubs) == 1:
        return graph.nodes[hubs[0]]["title"]
    areas = []
    for node in matched:
        for neighbor in graph.neighbors(node):
            if neighbor in _area_ids() and neighbor not in areas:
                areas.append(neighbor)
    if len(areas) == 1:
        return graph.nodes[areas[0]]["title"]
    return ""


def _matched_nodes(text: str) -> list[str]:
    blob = f" {normalized(text)} "
    hits = []
    for node, data in heritage_graph().nodes(data=True):
        if any(f" {normalized(alias)} " in blob for alias in data["aliases"]):
            hits.append(node)
    return hits

def _usable_title(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    title = " ".join(value.split())
    if not title or title == "Điểm đang chọn" or len(title) > 80 or not allowed_output(title):
        return None
    return title


def artifact_title_from_data(
    *, focus_title: str | None = None, graph_context: list[dict] | None = None, evidence=(),
) -> str | None:
    """Return an artifact name only when this turn's data already identifies it."""
    verified = _usable_title(focus_title)
    if verified:
        return verified
    for item in graph_context or []:
        if isinstance(item, dict) and item.get("type") == "artifact":
            title = _usable_title(item.get("title"))
            if title:
                return title
    for item in evidence or ():
        title = _usable_title(getattr(item, "artifact_title", None))
        if title:
            return title
    return None


def _entity_title(asked: str, area_title: str | None) -> str | None:
    matched = _matched_nodes(asked)
    hubs = _area_ids()
    parts = [node for node in matched if node not in hubs]
    if matched and len(parts) <= 1:
        return heritage_graph().nodes[parts[0] if parts else matched[0]]["title"]
    return area_title


def _prefer_identified_artifact(asked: str, artifact: str | None) -> bool:
    """Use the artifact only when this question is not about a different graph part."""
    if not artifact:
        return False
    if f" {normalized(artifact)} " in f" {normalized(asked)} ":
        return True
    return not any(node not in _area_ids() for node in _matched_nodes(asked))



def in_entity_follow_up(
    asked: str, *, area_title: str | None = None, focus_title: str | None = None,
    artifact_title: str | None = None,
) -> str | None:
    """Ask about the current entity; prefer its identified artifact, never a made-up name."""
    artifact = _usable_title(artifact_title or focus_title)
    use_artifact = _prefer_identified_artifact(asked, artifact)
    title = artifact if use_artifact else _entity_title(asked, area_title)
    if not title:
        return None
    host = (area_title or "").split("(", 1)[0].strip()
    subject = f"{title} trong {host}" if host and normalized(title) != normalized(host) else title
    templates = (
        f"Lịch sử của {subject} có gì đáng chú ý?",
        f"{subject} có gì đáng chú ý?" if use_artifact else f"{subject} gắn với nhân vật hoặc sự kiện nào?",
    )
    for question in templates:
        if normalized(question) != normalized(asked):
            return question
    return None


def ordered_entity_follow_ups(
    asked: str, *, area_title: str | None = None, artifact_title: str | None = None,
) -> list[str]:
    """Entity or identified-artifact question, then one NetworkX neighbor when present."""
    first = in_entity_follow_up(asked, area_title=area_title, artifact_title=artifact_title)
    accepted = [first] if first else []
    asked_norm = normalized(asked)
    for candidate in neighbor_follow_ups(asked, area_title=area_title):
        if normalized(candidate) == asked_norm or any(normalized(candidate) == normalized(item) for item in accepted):
            continue
        accepted.append(candidate)
        break
    return accepted



def related_entity_titles(text: str, *, limit: int = 3) -> list[str]:
    """Neighbor titles of entities mentioned in the question (exclude already named)."""
    matched = _matched_nodes(text)
    if not matched:
        return []
    graph = heritage_graph()
    matched_set = set(matched)
    titles: list[str] = []
    for node in matched:
        for neighbor in graph.neighbors(node):
            if neighbor in matched_set:
                continue
            title = graph.nodes[neighbor]["title"]
            if title not in titles:
                titles.append(title)
            if len(titles) == limit:
                return titles
    return titles


def neighbor_follow_ups(asked: str, *, area_title: str | None = None, limit: int = 3) -> list[str]:
    host = _host_title(asked, area_title)
    questions = []
    for title in related_entity_titles(asked, limit=limit):
        if host and normalized(title) != normalized(host):
            questions.append(f"{title} trong {host} có gì đặc biệt?")
        else:
            questions.append(f"{title} có gì đặc biệt?")
    return questions
