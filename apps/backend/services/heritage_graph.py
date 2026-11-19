"""In-process heritage-complex graph for related follow-up entities."""
from __future__ import annotations

from functools import lru_cache

import networkx as nx

from apps.backend.services.tour_scope import normalized

# Hub → parts inside one complex. Aliases must match user questions.
_COMPLEXES: tuple[dict, ...] = (
    {
        "hub": ("lang-tu-duc", "Lăng Tự Đức", ("Lăng Tự Đức", "Khiêm Lăng", "Khiêm Cung", "Vạn Niên Cơ")),
        "parts": (
            ("bi-dinh", "Bi Đình", ("Bi Đình", "Bi Dinh")),
            ("hoa-khiem", "Điện Hòa Khiêm", ("Điện Hòa Khiêm", "Hòa Khiêm Điện", "Hòa Khiêm")),
            ("mo-tu-duc", "khu mộ vua Tự Đức", ("khu mộ vua Tự Đức", "mộ vua Tự Đức", "khu mộ")),
        ),
    },
)


@lru_cache(maxsize=1)
def heritage_graph() -> nx.Graph:
    graph = nx.Graph()
    for complex_ in _COMPLEXES:
        hub_id, hub_title, hub_aliases = complex_["hub"]
        graph.add_node(hub_id, title=hub_title, aliases=hub_aliases)
        for part_id, part_title, part_aliases in complex_["parts"]:
            graph.add_node(part_id, title=part_title, aliases=part_aliases)
            graph.add_edge(hub_id, part_id, kind="contains")
    return graph


def _matched_nodes(text: str) -> list[str]:
    blob = f" {normalized(text)} "
    hits = []
    for node, data in heritage_graph().nodes(data=True):
        if any(f" {normalized(alias)} " in blob for alias in data["aliases"]):
            hits.append(node)
    return hits


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
    host = (area_title or "Khiêm Lăng").split("(", 1)[0].strip()
    questions = []
    for title in related_entity_titles(asked, limit=limit):
        if normalized(title) == normalized(host):
            questions.append(f"{title} có gì đặc biệt?")
        else:
            questions.append(f"{title} trong {host} có gì đặc biệt?")
    return questions
