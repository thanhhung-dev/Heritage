"""Heritage public API — Story 4.

Endpoints:
- GET /api/heritages                    → homepage list
- GET /api/heritages/{heritage_slug}    → FULL single-load content (heritage + full scenes)

Mirrors CyArk Tapestry /content/{slug}: one request returns the whole tour,
so the client does not need per-scene requests.
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
    SkyPresetOut,
    VoiceClipOut,
    VoiceOut,
)
from apps.backend.services.heritageServices import HeritageService, scene_slug

router = APIRouter(prefix="/heritages", tags=["heritage"])



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_service(db: AsyncSession = Depends(get_db)) -> HeritageService:
    return HeritageService(db)



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


def _scene_detail_out(sc, policy: AssetUrlPolicy) -> SceneDetailOut:
    """Serialize a full Scene ORM row into SceneDetailOut (no per-scene needs)."""
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
        id=sc.id,
        slug=scene_slug(sc.sequence),
        title=sc.title,
        description=sc.description,
        sequence=sc.sequence,
        sky=sky_out,
        camera=camera_out,
        voice_clips=voices_out,
        models=models_out,
        media=media_out,
        interactive=interactive_out,
        highlights=highlights_out,
    )



@router.get("", response_model=list[HeritageOut])
async def list_heritages(service: HeritageService = Depends(get_service)):
    """Homepage — list published heritages."""
    items = await service.list_published()
    results = []
    for item in items:
        out = _heritage_out(item["heritage"], item["voices"], item["voice_length"])
        results.append(out)
    return results



@router.get(
    "/{heritage_slug}",
    response_model=HeritageContentOut,
    responses={404: {"model": ErrorResponse}},
)
async def get_heritage_content(
    heritage_slug: str,
    service: HeritageService = Depends(get_service),
):
    """FULL single-load content — heritage info + overview intro + every scene
    (with camera, models, media, voice clips, interactives, highlights).
    No per-scene request."""
    data = await service.get_content_by_slug(heritage_slug)
    if data is None:
        return _error(404, "HERITAGE_NOT_FOUND", f"Heritage '{heritage_slug}' not found")

    heritage_out = _heritage_out(data["heritage"], data["voices"], data["voice_length"])
    policy = asset_policy()
    overview_out = (
        _scene_detail_out(data["overview"], policy)
        if data["overview"] is not None
        else None
    )
    scenes_out = [
        _scene_detail_out(sc, policy)
        for sc in data["scenes"]
    ]

    return HeritageContentOut(
        heritage=heritage_out,
        overview=overview_out,
        scenes=scenes_out,
    )