"""Service layer cho Tour — truy vấn DB thay thế cho v_tour_stop view.

Schema.sql comment tại view (L514-578) cho rằng: API lấy cả tour trong 1 query
qua v_tour_stop, tránh N+1. Service này là lớp trừu tượng nhẹ trên view đó.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.tour import TourStop


class TourService:
    """Read-only service trên v_tour_stop view.

    Lazy: không có write operation vì tour được quản lý qua admin UI riêng.
    Nếu cần thêm endpoint admin CRUD, mở rộng thành BaseService[Tour].
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_published_tour(
        self, slug: str, locale: str = "vi"
    ) -> list[TourStop]:
        """Trả về toàn bộ stops của một tour đã published, sắp xếp theo order_index.

        Truy vấn trực tiếp view v_tour_stop — 1 query cho cả tour + narration
        + model_url + highlights (schema.sql thiết kế view đúng mục đích này).
        """
        rows = await self.db.execute(
            select(TourStop)
            .where(
                TourStop.__table__.c.slug == slug,
                TourStop.__table__.c.locale == locale,
                TourStop.__table__.c.published_at.is_not(None),
            )
            .order_by(TourStop.__table__.c.order_index)
        )
        return list(rows.scalars().all())

    async def get_tour_metum(
        self, slug: str, locale: str = "vi"
    ) -> dict[str, Any] | None:
        """Trả về metadata tour (không có stops) để render trang bài viết."""
        rows = await self.db.execute(
            select(
                TourStop.__table__.c.slug,
                TourStop.__table__.c.locale,
                TourStop.__table__.c.tour_title,
                TourStop.__table__.c.tagline,
                TourStop.__table__.c.location_label,
                TourStop.__table__.c.splash_image_url,
                TourStop.__table__.c.ambient_audio_url,
                TourStop.__table__.c.default_camera_clip_url,
                TourStop.__table__.c.published_at,
            )
            .where(
                TourStop.__table__.c.slug == slug,
                TourStop.__table__.c.locale == locale,
                TourStop.__table__.c.published_at.is_not(None),
            )
            .limit(1)
        )
        row = rows.first()
        if not row:
            return None
        return {
            "slug": row.slug,
            "locale": row.locale,
            "title": row.tour_title,
            "tagline": row.tagline,
            "location_label": row.location_label,
            "splash_image_url": row.splash_image_url,
            "ambient_audio_url": row.ambient_audio_url,
            "default_camera_clip_url": row.default_camera_clip_url,
            "published_at": row.published_at.isoformat() if row.published_at else None,
        }
