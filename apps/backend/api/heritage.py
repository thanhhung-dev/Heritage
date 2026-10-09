"""Heritage public API — Story 4.

Endpoints:
- GET /api/heritage                                → homepage list
- GET /api/heritage/{heritage_slug}                → content overview
- GET /api/heritage/{heritage_slug}/scenes/{key}   → scene detail
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.assets import AssetUrlPolicy, asset_policy
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.schemas.heritage import (
    CameraOut,
    ErrorDetail,
    ErrorResponse,
    HeritageContentOut,
    HeritageOut,
    InteractiveHighlightOut,
    InteractiveOut,
    MediaItemOut,
    ModelAssetOut,
    SceneDetailOut,
    SceneHighlightOut,
    SceneOut,
    SkyPresetOut,
    VoiceClipOut,
    VoiceOut,
)
from apps.backend.services.heritageServices import (
    HeritageService,
    parse_scene_key,
    scene_slug,
)

router = APIRouter(prefix="/heritage", tags=["heritage"])


# ── Dependencies ───────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_service(db: AsyncSession = Depends(get_db)) -> HeritageService:
    return HeritageService(db)


# ── Helpers ────────────────────────────────────────────────────────

def _heritage_out(heritage, voices, voice_length) -> HeritageOut:
    """Build HeritageOut with computed voices field."""
    policy = asset_policy()
    out = HeritageOut.model_validate(heritage)
    out.voices = [VoiceOut.model_validate(v) for v in voices]
    out.voice_length = voice_length
    _resolve_urls(
        out,
        policy,
        "card_image_url",
        "splash_image_url",
        "hover_video_url",
        "presented_by_logo_url",
    )
    for voice in out.voices:
        _resolve_urls(voice, policy, "headshot_url", "intro_video_url")
    return out


def _resolve_urls(model: BaseModel, policy: AssetUrlPolicy, *fields: str) -> None:
    """Apply the R2 asset URL policy to URL fields of a response model in place."""
    for name in fields:
        setattr(model, name, policy.resolve(getattr(model, name)))


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=ErrorDetail(code=code, message=message)
        ).model_dump(),
    )


# ── GET /api/heritage ─────────────────────────────────────────────

@router.get("", response_model=list[HeritageOut])
async def list_heritages(service: HeritageService = Depends(get_service)):
    """Homepage — list published heritages."""
    items = await service.list_published()
    results = []
    for item in items:
        out = _heritage_out(item["heritage"], item["voices"], item["voice_length"])
        results.append(out)
    return results


# ── GET /api/heritage/{heritage_slug} ──────────────────────────────

@router.get(
    "/{heritage_slug}",
    response_model=HeritageContentOut,
    responses={404: {"model": ErrorResponse}},
)
async def get_heritage_content(
    heritage_slug: str,
    service: HeritageService = Depends(get_service),
):
    """Content overview — heritage info + scene list."""
    data = await service.get_content_by_slug(heritage_slug)
    if data is None:
        return _error(404, "HERITAGE_NOT_FOUND", f"Heritage '{heritage_slug}' not found")

    heritage_out = _heritage_out(data["heritage"], data["voices"], data["voice_length"])
    scenes_out = [
        SceneOut(
            id=sc.id,
            slug=scene_slug(sc.sequence),
            title=sc.title,
            description=sc.description,
            sequence=sc.sequence,
        )
        for sc in data["scenes"]
    ]

    return HeritageContentOut(heritage=heritage_out, scenes=scenes_out)


# ── GET /api/heritage/{heritage_slug}/scenes/{scene_key} ───────────

@router.get(
    "/{heritage_slug}/scenes/{scene_key}",
    response_model=SceneDetailOut,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def get_scene_detail(
    heritage_slug: str,
    scene_key: str,
    service: HeritageService = Depends(get_service),
):
    """Scene detail — full scene data with models, camera, sky, voices, media, etc."""
    sequence = parse_scene_key(scene_key)
    if sequence is None:
        return _error(
            400,
            "INVALID_SCENE_KEY",
            f"Scene key '{scene_key}' is invalid. Expected format: s1, s2, s3, ...",
        )

    data = await service.get_scene_detail(heritage_slug, sequence)

    if data is None:
        # Determine if heritage or scene is missing
        heritage = await service.get_by_slug(heritage_slug)
        if heritage is None:
            return _error(404, "HERITAGE_NOT_FOUND", f"Heritage '{heritage_slug}' not found")
        return _error(404, "SCENE_NOT_FOUND", f"Scene '{scene_key}' not found")

    heritage_out = _heritage_out(data["heritage"], data["voices"], data["voice_length"])
    sc = data["scene"]

    scene_out = SceneOut(
        id=sc.id,
        slug=scene_slug(sc.sequence),
        title=sc.title,
        description=sc.description,
        sequence=sc.sequence,
    )

    camera_out = CameraOut(
        node_name=sc.camera_node_name,
        start_position=sc.cam_start_pos,
        start_target=sc.cam_start_target,
        zoom_position=sc.cam_zoom_pos,
        zoom_target=sc.cam_zoom_target,
        instant_move=sc.instant_move,
    )

    sky_out = (
        SkyPresetOut.model_validate(sc.sky_preset)
        if sc.sky_preset is not None
        else None
    )

    models_out = [ModelAssetOut.model_validate(m) for m in sc.model_assets]

    voices_out = [
        VoiceClipOut(
            id=clip.id,
            video_url=clip.video_url,
            audio_url=clip.audio_url,
            bubble_text=clip.bubble_text,
            sort_order=clip.sort_order,
            voice=VoiceOut.model_validate(clip.voice),
        )
        for clip in sorted(sc.voice_clips, key=lambda c: c.sort_order)
    ]

    media_out = [
        MediaItemOut.model_validate(m)
        for m in sorted(sc.media_items, key=lambda m: m.sort_order)
    ]

    interactive_out = [
        InteractiveOut(
            id=inter.id,
            mode=inter.mode,
            cam_pos=inter.cam_pos,
            cam_target=inter.cam_target,
            explore_area=inter.explore_area,
            highlights=[
                InteractiveHighlightOut.model_validate(h)
                for h in sorted(inter.highlights, key=lambda h: h.sort_order)
            ],
        )
        for inter in sc.interactives
    ]

    highlights_out = [SceneHighlightOut.model_validate(h) for h in sc.scene_highlights]

    policy = asset_policy()
    for model in models_out:
        _resolve_urls(model, policy, "file_url")
    for clip in voices_out:
        _resolve_urls(clip, policy, "video_url", "audio_url")
        _resolve_urls(clip.voice, policy, "headshot_url", "intro_video_url")
    for item in media_out:
        _resolve_urls(item, policy, "asset_url", "thumb_url")
    for inter in interactive_out:
        for highlight in inter.highlights:
            _resolve_urls(highlight, policy, "media_url")
    for scene_highlight in highlights_out:
        _resolve_urls(scene_highlight, policy, "model_url")

    return SceneDetailOut(
        heritage=heritage_out,
        scene=scene_out,
        models=models_out,
        sky=sky_out,
        camera=camera_out,
        voices=voices_out,
        media=media_out,
        interactive=interactive_out,
        highlights=highlights_out,
    )