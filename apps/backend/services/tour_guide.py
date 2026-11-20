"""Server-owned tour identity and editorial story branches (not historical evidence)."""
from dataclasses import dataclass

from sqlalchemy import select

from apps.backend.api.public.chat.schemas import GuideStory, TourReplyContext
from apps.backend.models.heritage import Heritage
from apps.backend.models.scene import Scene
from apps.backend.models.interactive import Interactive
from apps.backend.models.interactive_highlight import InteractiveHighlight
from apps.backend.models.interactive_highlight_passage import InteractiveHighlightPassage
from apps.backend.services.tour_scope import resolve_area

GUIDE_STORIES: dict[tuple[str, str, str | None], tuple[GuideStory, ...]] = {}



@dataclass
class TourFocus:
    """A display label for the selected point, never historical evidence."""

    title: str

    def questions(self) -> list[str]:
        return [
            f"{self.title} có đặc điểm gì đáng chú ý?",
            f"{self.title} gắn với những nhân vật hoặc sự kiện nào?",
            f"Tư liệu nào giải thích ý nghĩa của {self.title}?",
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
    passage_links = {}
    if context.mode != "scene":
        if context.highlight_id is not None:
            query = select(Interactive.mode, InteractiveHighlight.popup_title).join(
                InteractiveHighlight, InteractiveHighlight.interactive_id == Interactive.id,
            ).where(
                Interactive.scene_id == row.id,
                InteractiveHighlight.id == context.highlight_id,
            )
            points = (await db.execute(query)).all()
        else:
            query = select(Interactive.mode).where(Interactive.scene_id == row.id)
            points = [(mode, None) for (mode,) in (await db.execute(query)).all()]
        matching = [point for point in points if (
            "walk" if point[0] == "free_explore" else "free" if point[0] == "free" else "standard"
        ) == context.mode]
        if not matching:
            raise ValueError("Chế độ hoặc điểm được chọn không thuộc cảnh đang tham quan.")
        if context.highlight_id is not None:
            title = matching[0][1]
            links = (await db.execute(select(
                InteractiveHighlightPassage.passage_id, InteractiveHighlightPassage.content_hash,
                InteractiveHighlightPassage.object_key, InteractiveHighlightPassage.bucket,
            ).where(InteractiveHighlightPassage.highlight_id == context.highlight_id))).all()
            passage_links = {passage_id: {"content_hash": content_hash,
                                           "object_key": object_key, "bucket": bucket}
                             for passage_id, content_hash, object_key, bucket in links}
    stories = guide_stories(request.active_area_id, row.title, title)
    if context.story_id is not None:
        story = next((story for story in stories if story.id == context.story_id), None)
        if story is None or request.message.strip() != story.question:
            raise ValueError("Câu chuyện chưa được duyệt cho yêu cầu và điểm đang tham quan.")
    return TourReplyContext(
        scene_id=row.id, scene_key=f"s{row.sequence + 1}", scene_title=row.title[:200],
        mode=context.mode, highlight_id=context.highlight_id,
        highlight_title=title[:200] if title else None, passage_links=passage_links,
        story_id=context.story_id,
    )
