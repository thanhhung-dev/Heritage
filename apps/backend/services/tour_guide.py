"""Server-owned tour identity and editorial story branches (not historical evidence)."""
from dataclasses import dataclass

from sqlalchemy import select

from apps.backend.api.public.chat.schemas import GuideStory, TourReplyContext
from apps.backend.models.heritage import Heritage
from apps.backend.models.scene import Scene
from apps.backend.models.interactive import Interactive
from apps.backend.models.interactive_highlight import InteractiveHighlight
from apps.backend.services.tour_scope import normalized, resolve_area

GUIDE_STORIES: dict[tuple[str, str, str | None], tuple[GuideStory, ...]] = {}



@dataclass
class TourArtifact:
    """Editorial identity and evidence scope; popup copy is never evidence."""

    id: str
    title: str
    aliases: tuple[str, ...]
    source_ids: frozenset[str]
    artifact_key: str | None = None
    def questions(self) -> list[str]:
        return [
            f"{self.title} có đặc điểm gì đáng chú ý?",
            f"{self.title} gắn với những nhân vật hoặc sự kiện nào?",
            f"Tư liệu nào giải thích ý nghĩa của {self.title}?",
        ]


# Compatibility-only registry for legacy fixtures. Production marker identity
# comes from interactive_highlight.artifact_key.
TOUR_ARTIFACTS: dict[tuple[str, int, int], TourArtifact] = {}

# Compatibility-only classification for legacy fixtures. New markers are
# classified by whether the database supplies artifact_key.
TOUR_NON_ARTIFACT_MARKERS: set[tuple[str, int, int]] = set()


def marker_is_verified_non_artifact(area_id: str, scene_id: int, highlight_id: int | None) -> bool:
    return highlight_id is not None and (area_id, scene_id, highlight_id) in TOUR_NON_ARTIFACT_MARKERS


def tour_artifact(area_id: str, scene_id: int, highlight_id: int | None) -> TourArtifact | None:
    if highlight_id is None:
        return None
    return TOUR_ARTIFACTS.get((area_id, scene_id, highlight_id))


def referenced_tour_artifacts(
    area_id: str, text: str, *, exclude_id: str | None = None,
) -> list[TourArtifact]:
    """Return every matching editorial point so duplicate labels stay ambiguous."""
    value = f" {normalized(text)} "
    return [
        artifact for (registered_area, _scene_id, _highlight_id), artifact in TOUR_ARTIFACTS.items()
        if registered_area == area_id and artifact.id != exclude_id
        and any(f" {normalized(name)} " in value for name in (artifact.title, *artifact.aliases))
    ]


def guide_stories(area_id: str, scene_title: str, highlight_title: str | None = None) -> list[GuideStory]:
    return list(GUIDE_STORIES.get((area_id, scene_title, highlight_title), ()))[:3]


async def resolve_tour_context(request, db) -> TourReplyContext:
    context = request.tour_context
    row = (await db.execute(
        select(Scene.id, Scene.sequence, Scene.title, Heritage.slug)
        .join(Heritage, Heritage.id == Scene.heritage_id)
        .where(Scene.id == context.scene_id, Heritage.id == request.heritage_id,
               Heritage.publish_state == "published")
    )).first()
    if row is None or resolve_area(row.slug).id != request.active_area_id:
        raise ValueError("Cảnh không thuộc di sản và khu vực đang tham quan.")
    title = None
    artifact_key = None
    if context.mode != "scene":
        if context.highlight_id is not None:
            try:
                query = select(
                    Interactive.mode, InteractiveHighlight.popup_title,
                    InteractiveHighlight.artifact_key,
                ).join(
                    InteractiveHighlight, InteractiveHighlight.interactive_id == Interactive.id,
                ).where(
                    Interactive.scene_id == row.id,
                    InteractiveHighlight.id == context.highlight_id,
                )
                points = (await db.execute(query)).all()
            except Exception:
                # Compatibility with read-only fixtures created before artifact_key.
                query = select(Interactive.mode, InteractiveHighlight.popup_title).join(
                    InteractiveHighlight, InteractiveHighlight.interactive_id == Interactive.id,
                ).where(
                    Interactive.scene_id == row.id,
                    InteractiveHighlight.id == context.highlight_id,
                )
                points = [(mode, popup_title, None) for mode, popup_title in (await db.execute(query)).all()]
        else:
            query = select(Interactive.mode).where(Interactive.scene_id == row.id)
            points = [(mode, None, None) for (mode,) in (await db.execute(query)).all()]
        matching = [point for point in points if (
            "walk" if point[0] == "free_explore" else "free" if point[0] == "free" else "standard"
        ) == context.mode]
        if not matching:
            raise ValueError("Chế độ hoặc điểm được chọn không thuộc cảnh đang tham quan.")
        if context.highlight_id is not None:
            title = matching[0][1]
            artifact_key = matching[0][2]
    stories = guide_stories(request.active_area_id, row.title, title)
    if context.story_id is not None:
        story = next((story for story in stories if story.id == context.story_id), None)
        if story is None or request.message.strip() != story.question:
            raise ValueError("Câu chuyện chưa được duyệt cho yêu cầu và điểm đang tham quan.")
    return TourReplyContext(
        scene_id=row.id, scene_key=f"s{row.sequence + 1}", scene_title=row.title[:200],
        mode=context.mode, highlight_id=context.highlight_id,
        highlight_title=title[:200] if title else None, artifact_key=artifact_key,
        story_id=context.story_id,
    )
