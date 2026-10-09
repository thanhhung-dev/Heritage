"""Service layer cho Heritage public API (Story 4).

Provides:
- list_published()          → homepage list
- get_by_slug()             → heritage detail
- get_content_by_slug()     → heritage + scenes (content overview)
- get_scene_detail()        → full scene detail
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from apps.backend.models.heritage import Heritage
from apps.backend.models.interactive import Interactive
from apps.backend.models.scene import Scene
from apps.backend.models.voice import Voice
from apps.backend.models.voice_clip import VoiceClip


# ── Helpers ────────────────────────────────────────────────────────

_SCENE_KEY_RE = re.compile(r"^s(\d+)$")


def parse_scene_key(scene_key: str) -> int | None:
    """Parse 's1' → sequence 0, 's2' → sequence 1, etc.  Returns None if invalid."""
    m = _SCENE_KEY_RE.match(scene_key)
    if not m:
        return None
    num = int(m.group(1))
    if num < 1:
        return None
    return num - 1  # 0-based sequence


def scene_slug(sequence: int) -> str:
    """Derive scene route key from 0-based sequence: 0 → 's1', 1 → 's2', ..."""
    return f"s{sequence + 1}"


def _collect_unique_voices(heritage: Heritage) -> list[Voice]:
    """Collect unique Voice entities across all scenes of a heritage.

    Voice is linked via VoiceClip → Scene → Heritage; there is NO direct
    Heritage → Voice FK in the database.
    """
    seen: set[int] = set()
    voices: list[Voice] = []
    for sc in heritage.scenes:
        for clip in sc.voice_clips:
            if clip.voice_id not in seen:
                seen.add(clip.voice_id)
                voices.append(clip.voice)
    return voices


# ── Service ────────────────────────────────────────────────────────

class HeritageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Homepage ───────────────────────────────────────────────────

    async def list_published(self) -> list[dict[str, Any]]:
        """Return published heritages with computed voices for homepage."""
        stmt = (
            select(Heritage)
            .where(Heritage.publish_state == "published")
            .options(
                selectinload(Heritage.language1),
                selectinload(Heritage.language2),
                selectinload(Heritage.scenes)
                .selectinload(Scene.voice_clips)
                .selectinload(VoiceClip.voice),
            )
            .order_by(Heritage.id)
        )
        heritages = list((await self.db.execute(stmt)).scalars().unique().all())

        results = []
        for h in heritages:
            voices = _collect_unique_voices(h)
            results.append({
                "heritage": h,
                "voices": voices,
                "voice_length": len(voices),
            })
        return results

    # ── Content overview ───────────────────────────────────────────

    async def get_by_slug(self, slug: str) -> Heritage | None:
        """Return a single published heritage by slug (with languages loaded)."""
        stmt = (
            select(Heritage)
            .where(Heritage.slug == slug, Heritage.publish_state == "published")
            .options(
                selectinload(Heritage.language1),
                selectinload(Heritage.language2),
                selectinload(Heritage.scenes)
                .selectinload(Scene.voice_clips)
                .selectinload(VoiceClip.voice),
            )
        )
        return (await self.db.execute(stmt)).scalars().unique().first()

    async def get_content_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Return heritage + scenes for content overview page."""
        heritage = await self.get_by_slug(slug)
        if heritage is None:
            return None

        voices = _collect_unique_voices(heritage)

        return {
            "heritage": heritage,
            "voices": voices,
            "voice_length": len(voices),
            "scenes": heritage.scenes,
        }

    # ── Scene detail ───────────────────────────────────────────────

    async def get_scene_detail(
        self, slug: str, sequence: int
    ) -> dict[str, Any] | None:
        """Return full scene detail for a heritage by slug + scene sequence.

        Returns None if the heritage or scene is not found.
        """
        heritage = await self.get_by_slug(slug)
        if heritage is None:
            return None

        # Find scene by sequence
        scene: Scene | None = None
        for sc in heritage.scenes:
            if sc.sequence == sequence:
                scene = sc
                break

        if scene is None:
            return None

        # Reload scene with all eager-loaded relationships
        stmt = (
            select(Scene)
            .where(Scene.id == scene.id)
            .options(
                selectinload(Scene.model_assets),
                selectinload(Scene.voice_clips).selectinload(VoiceClip.voice),
                selectinload(Scene.media_items),
                selectinload(Scene.interactives).selectinload(
                    Interactive.highlights
                ),
                selectinload(Scene.scene_highlights),
                joinedload(Scene.sky_preset),
            )
        )
        scene = (await self.db.execute(stmt)).scalars().unique().first()

        voices = _collect_unique_voices(heritage)

        return {
            "heritage": heritage,
            "voices": voices,
            "voice_length": len(voices),
            "scene": scene,
        }