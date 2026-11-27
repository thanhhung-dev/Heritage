"""Public reference lookup used only when the local corpus cannot answer."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote

import httpx

_API = "https://vi.wikipedia.org/w/api.php"
_HEADERS = {"User-Agent": "HeritageGraph/1.0 (local tour research; contact: dev@heritagegraph.local)"}


@dataclass(frozen=True)
class PublicReference:
    title: str
    url: str
    extract: str


def _matches_area(title: str, names: list[str]) -> bool:
    if not names:
        return bool(title.strip())
    folded = title.casefold()
    return any(name.casefold() in folded for name in names)

def _identity_name(question: str) -> str | None:
    match = re.search(r"(?i)(.+?)\s+là ai\b", question.strip())
    if not match:
        return None
    name = re.sub(r"(?i)^(ông|bà|vua|hoàng đế)\s+", "", match.group(1)).strip(" ?.,")
    return name or None


def _name_belongs_to_area(name: str, names: list[str]) -> bool:
    folded = name.casefold()
    return any(folded in area.casefold() for area in names)
def _subject(question: str, names: list[str]) -> str:
    """The name the user actually asked about, if it belongs to this area."""
    asked = question.casefold()
    mentioned = [name for name in names if name.casefold() in asked]
    if mentioned:
        return max(mentioned, key=len)
    pieces = []
    for name in names:
        parts = name.split()
        for size in range(1, len(parts)):
            for start in range(len(parts) - size + 1):
                piece = " ".join(parts[start:start + size])
                if len(piece) >= 3 and piece.casefold() in asked:
                    pieces.append(piece)
    return max(pieces, key=len) if pieces else ""


def answer_from_page(question: str, item: PublicReference, generate) -> str | None:
    """The model answers the question from the page. No per-question-type rules."""
    try:
        raw = generate(
            question=question,
            context=item.extract[:4500],
            conversation=False,
            max_tokens=220,
        )
    except Exception:
        return None
    spoken = (raw or "").strip()
    if not spoken or spoken.startswith("{") or len(spoken) < 20:
        spoken = item.extract.split(".")[0].strip()
    if not spoken:
        return None
    if not spoken.endswith("."):
        spoken += "."
    return f"{spoken}\n\nĐây là nguồn tham khảo: {item.title} — {item.url}"


def reference_answer(item: PublicReference, question: str = "") -> str | None:
    del question
    body = " ".join(item.extract.split())
    if len(body) > 420:
        body = body[:420].rsplit(" ", 1)[0].rstrip(".,;")
    if len(body) < 40:
        return None
    return f"{body}\n\nĐây là nguồn tham khảo: {item.title} — {item.url}"




async def research_heritage(
    question: str, area_title: str = "", aliases: tuple[str, ...] = (),
) -> PublicReference | None:
    """One Vietnamese Wikipedia page for this area. A unrelated first hit is not a source."""
    names = [name.strip() for name in (area_title, *aliases) if name and name.strip()]
    subject = _subject(question, names)
    query = (subject or area_title or question).strip()[:180]
    if not query:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0, headers=_HEADERS, follow_redirects=True) as client:
            found = await client.get(_API, params={
                "action": "query", "list": "search", "srsearch": query,
                "srlimit": 5, "format": "json", "utf8": 1,
            })
            found.raise_for_status()
            hits = found.json().get("query", {}).get("search") or []
            titles = [str(hit.get("title") or "").strip() for hit in hits]
            wanted = subject.casefold()
            title = next((item for item in titles if item.casefold() == wanted), "")
            if not title:
                title = next((item for item in titles if _matches_area(item, names)), "")
            if not title:
                return None
            page = await client.get(_API, params={
                "action": "query", "prop": "extracts", "explaintext": 1,
                "titles": title, "redirects": 1, "format": "json", "utf8": 1,
            })
            page.raise_for_status()
            pages = page.json().get("query", {}).get("pages") or {}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None
    extract = ""
    resolved = title
    for page in pages.values():
        if not isinstance(page, dict) or page.get("missing"):
            continue
        resolved = str(page.get("title") or title)
        extract = str(page.get("extract") or "")
        break
    extract = " ".join(extract.split())
    if len(extract) < 40 or not (_matches_area(resolved, names) or resolved.casefold() == subject.casefold()):
        return None
    return PublicReference(
        title=resolved,
        url=f"https://vi.wikipedia.org/wiki/{quote(resolved.replace(' ', '_'))}",
        extract=extract,
    )
