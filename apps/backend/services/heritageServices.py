"""Service layer cho Heritage public API (Story 4).

Provides:
- list_published()          → homepage list
- get_by_slug()             → heritage detail (languages + full scenes loaded)
- get_content_by_slug()     → heritage + full scenes (single-load content page)
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.models.heritage import Heritage
from apps.backend.models.interactive import Interactive
from apps.backend.models.scene import Scene
from apps.backend.models.voice_clip import VoiceClip



def scene_slug(sequence: int) -> str:
    """Derive scene route key from 0-based sequence: 0 → 's1', 1 → 's2', ..."""
    return f"s{sequence + 1}"



class HeritageService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def list_published(self) -> list[dict[str, Any]]:
        """Return published heritages with computed voices for homepage."""
        stmt = (
            select(Heritage)
            .where(Heritage.publish_state == "published")
            .options(
                selectinload(Heritage.language1),
                selectinload(Heritage.language2),
                selectinload(Heritage.voices),
                selectinload(Heritage.scenes)
                .selectinload(Scene.voice_clips)
                .selectinload(VoiceClip.voice),
            )
            .order_by(Heritage.id)
        )
        heritages = list((await self.db.execute(stmt)).scalars().unique().all())

        results = []
        for h in heritages:
            voices = list(h.voices)
            results.append({
                "heritage": h,
                "voices": voices,
                "voice_length": len(voices),
            })
        return results


    async def _load_heritage(self, stmt) -> Heritage | None:
        return (await self.db.execute(stmt)).scalars().unique().first()

    async def get_by_slug(self, slug: str) -> Heritage | None:
        """Return a single published heritage by slug (with languages + scenes loaded)."""
        stmt = (
            select(Heritage)
            .where(Heritage.slug == slug, Heritage.publish_state == "published")
            .options(
                selectinload(Heritage.language1),
                selectinload(Heritage.language2),
                selectinload(Heritage.voices),
                selectinload(Heritage.scenes)
                .selectinload(Scene.voice_clips)
                .selectinload(VoiceClip.voice),
                selectinload(Heritage.scenes).selectinload(Scene.model_assets),
                selectinload(Heritage.scenes).selectinload(Scene.sky_preset),
                selectinload(Heritage.scenes).selectinload(Scene.media_items),
                selectinload(Heritage.scenes)
                .selectinload(Scene.interactives)
                .selectinload(Interactive.highlights),
                selectinload(Heritage.scenes).selectinload(Scene.scene_highlights),
            )
        )
        return await self._load_heritage(stmt)

    async def get_content_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Return heritage + full scenes for content page (single load)."""
        heritage = await self.get_by_slug(slug)
        if heritage is None:
            return None

        voices = list(heritage.voices)

        return {
            "heritage": heritage,
            "voices": voices,
            "voice_length": len(voices),
            "scenes": heritage.scenes,
        }