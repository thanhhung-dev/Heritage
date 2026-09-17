"""Tour 3D controller — serve published tours từ DB qua v_tour_stop view.

Schema.sql thiết kế: API đọc view v_tour_stop (1 query cho cả tour).
Controller này là thin layer: parse query params → gọi TourService → trả JSON.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from backend.db.base import AsyncSessionLocal
from backend.services.tour import TourService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tours", tags=["tours"])


def _fmt_vec3(v: list[float] | None) -> str | None:
    """Convert [x,y,z] array từ DB thành "x,y,z" string nếu FE cần (schema.sql note L512)."""
    if v is None or len(v) != 3:
        return None
    return ",".join(str(round(c, 4)) for c in v)


class TourStopResponse(BaseModel):
    """Mapping từ v_tour_stop row → JSON cho frontend Three.js."""
    story_id: str
    order_index: int
    title: str
    description: str | None = None
    scene_title: str | None = None
    scene_description: str | None = None
    bbox_min: str | None = None
    bbox_max: str | None = None
    transform_7dof: dict | None = None
    model_url: str | None = None
    camera_clip_url: str | None = None
    camera_name: str | None = None
    clip_start_s: float | None = None
    clip_end_s: float | None = None
    camera_fov: float | None = None
    pan_enable: bool = True
    instant_move: bool = False
    sky: str | None = None
    free_explore: bool = False
    explore_area: dict | None = None
    start_camera_position: str | None = None
    start_camera_target: str | None = None
    zoom_camera_position: str | None = None
    zoom_camera_target: str | None = None
    narration_url: str | None = None
    captions_vtt_url: str | None = None
    narration_duration_ms: int | None = None
    highlights: list[dict] = Field(default_factory=list)


class TourResponse(BaseModel):
    slug: str
    locale: str
    title: str
    tagline: str | None = None
    location_label: str | None = None
    splash_image_url: str | None = None
    ambient_audio_url: str | None = None
    default_camera_clip_url: str | None = None
    revision: int
    published_at: str | None = None
    stops: list[TourStopResponse] = Field(default_factory=list)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/{slug}", response_model=TourResponse)
async def get_tour(
    slug: str = Path(..., description="URL slug, ví dụ 'lang-tu-duc'"),
    locale: str = Query("vi", max_length=8),
    db: AsyncSession = Depends(get_db),
):
    """Lấy toàn bộ tour 3D đã published (1 query qua v_tour_stop view)."""
    service = TourService(db)
    stops = await service.get_published_tour(slug=slug, locale=locale)
    if not stops:
        raise HTTPException(
            status_code=404,
            detail=f"Tour '{slug}' (locale={locale}) không tìm thấy hoặc chưa được xuất bản",
        )

    meta = stops[0]
    return TourResponse(
        slug=meta.slug,
        locale=meta.locale,
        title=meta.tour_title,
        tagline=meta.tagline,
        location_label=meta.location_label,
        splash_image_url=meta.splash_image_url,
        ambient_audio_url=meta.ambient_audio_url,
        default_camera_clip_url=meta.default_camera_clip_url,
        revision=meta.revision,
        published_at=meta.published_at.isoformat() if meta.published_at else None,
        stops=[
            TourStopResponse(
                story_id=str(s.story_id),
                order_index=s.order_index,
                title=s.scene_title or "",
                description=s.scene_description,
                bbox_min=_fmt_vec3(s.bbox_min),
                bbox_max=_fmt_vec3(s.bbox_max),
                transform_7dof=s.transform_7dof,
                model_url=s.model_url,
                camera_clip_url=s.camera_clip_url,
                camera_name=s.camera_name,
                clip_start_s=float(s.clip_start_s) if s.clip_start_s else None,
                clip_end_s=float(s.clip_end_s) if s.clip_end_s else None,
                camera_fov=s.camera_fov,
                pan_enable=s.pan_enable,
                instant_move=s.instant_move,
                sky=s.sky,
                free_explore=s.free_explore,
                explore_area=s.explore_area,
                start_camera_position=_fmt_vec3(s.start_camera_position),
                start_camera_target=_fmt_vec3(s.start_camera_target),
                zoom_camera_position=_fmt_vec3(s.zoom_camera_position),
                zoom_camera_target=_fmt_vec3(s.zoom_camera_target),
                narration_url=s.narration_url,
                captions_vtt_url=s.captions_vtt_url,
                narration_duration_ms=s.narration_duration_ms,
                highlights=s.highlights if isinstance(s.highlights, list) else [],
            )
            for s in stops
        ],
    )
