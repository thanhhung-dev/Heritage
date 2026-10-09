"""Heritage detail controller: API công khai cho trang Content Landing.

Mỏng, giống api/tour.py: nhận tham số -> gọi service -> trả JSON.
Khác api/tour.py ở chỗ KHÔNG trả stops, model_url, narration_url
(landing không được tải trước 3D/audio).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.api.tour import get_db
from apps.backend.services.heritage import HeritageDetail, HeritageService

router = APIRouter(prefix="/heritage", tags=["heritage"])


class HeritageSource(BaseModel):
    title: str
    url: str | None = None
    license: str | None = None


class HeritageDetailResponse(BaseModel):
    slug: str
    locale: str
    title: str
    subtitle: str | None = None
    region: str
    location_label: str | None = None
    description: str | None = None
    hero_image_url: str | None = None
    revision: int
    published_at: str
    sources: list[HeritageSource] = Field(default_factory=list)
    scene_available: bool


def _to_response(detail: HeritageDetail) -> HeritageDetailResponse:
    sources: list[HeritageSource] = []
    if detail.source_title:
        sources.append(
            HeritageSource(
                title=detail.source_title,
                url=detail.source_url,
                license=detail.source_license,
            )
        )

    return HeritageDetailResponse(
        slug=detail.slug,
        locale=detail.locale,
        title=detail.title,
        subtitle=detail.subtitle,
        region=detail.region,
        location_label=detail.location_label,
        description=detail.description,
        hero_image_url=detail.hero_image_url,
        revision=detail.revision,
        published_at=detail.published_at.isoformat(),
        sources=sources,
        scene_available=detail.scene_available,
    )


@router.get("/{slug}", response_model=HeritageDetailResponse)
async def get_heritage_detail(
    slug: str = Path(..., min_length=1, max_length=200, description="URL slug, ví dụ 'lang-tu-duc'"),
    locale: str = Query("vi", min_length=2, max_length=8),
    db: AsyncSession = Depends(get_db),
):
    """Chi tiết di sản đã xuất bản để dựng trang Content Landing."""
    service = HeritageService(db)
    detail = await service.get_published_detail(slug=slug, locale=locale)
    if detail is None:
        # Không fallback sang locale khác hay bản nháp: không thấy là 404.
        raise HTTPException(
            status_code=404,
            detail=f"Di sản '{slug}' (locale={locale}) không tìm thấy hoặc chưa được xuất bản",
        )
    return _to_response(detail)