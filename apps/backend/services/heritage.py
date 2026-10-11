"""Service layer cho trang Content Landing (HER-33 / HER-104).

Chỉ đọc. Trả về thông tin giới thiệu NHẸ của một di sản đã xuất bản.
KHÔNG trả URL model 3D, audio hay stops: những thứ đó chỉ tải khi người dùng bấm Start.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.models import Document, ModelAsset, Site, Story, Tour


@dataclass(frozen=True)
class HeritageDetail:
    """Kết quả service trả về, tách khỏi SQL và khỏi Pydantic."""

    slug: str
    locale: str
    title: str
    subtitle: str | None
    region: str
    location_label: str | None
    description: str | None
    hero_image_url: str | None
    revision: int
    published_at: datetime
    source_title: str | None
    source_url: str | None
    source_license: str | None
    scene_available: bool


class HeritageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_published_detail(
        self, slug: str, locale: str = "vi"
    ) -> HeritageDetail | None:
        """Lấy chi tiết di sản đã xuất bản, hoặc None nếu không có."""

        # Cảnh "sẵn sàng" = tour có ít nhất một story gắn với scene
        # có model_asset thật (không phải bản proxy).
        # Chỉ kiểm tra tồn tại (EXISTS), không lấy URL nào ra ngoài.
        scene_available = (
            select(Story.id)
            .join(ModelAsset, ModelAsset.scene_id == Story.scene_id)
            .where(Story.tour_id == Tour.id, ModelAsset.is_proxy.is_(False))
            .exists()
        )

        stmt = (
            select(
                Tour.slug,
                Tour.locale,
                Tour.title,
                Tour.tagline,
                Tour.location_label,
                Tour.splash_image_url,
                Tour.revision,
                Tour.published_at,
                Site.region,
                Site.description,
                Document.title.label("source_title"),
                Document.source_url,
                Document.license,
                scene_available.label("scene_available"),
            )
            .select_from(Tour)
            .join(Site, Site.id == Tour.site_id)
            # OUTER JOIN: không có nguồn thì trang vẫn hiện, chỉ thiếu phần nguồn.
            .outerjoin(
                Document,
                and_(
                    Document.id == Site.source_document_id,
                    Document.withdrawn_at.is_(None),  # nguồn đã rút thì không hiện
                ),
            )
            .where(
                Tour.slug == slug,
                Tour.locale == locale,
                Tour.published_at.is_not(None),  # NULL = bản nháp, phải ẩn
            )
        )

        row = (await self.db.execute(stmt)).first()
        if row is None:
            return None

        return HeritageDetail(
            slug=row.slug,
            locale=row.locale,
            title=row.title,
            subtitle=row.tagline,
            region=row.region,
            location_label=row.location_label,
            description=row.description,
            hero_image_url=row.splash_image_url,
            revision=row.revision,
            published_at=row.published_at,
            source_title=row.source_title,
            source_url=row.source_url,
            source_license=row.license,
            scene_available=bool(row.scene_available),
        )