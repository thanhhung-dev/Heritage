"""Pydantic v2 response schemas for Heritage public API (Story 4).

Contracts (mirrors CyArk Tapestry single-load model):
- HeritageOut          — homepage list item
- SceneDetailOut       — full scene payload (camera, model, media, ...)
- HeritageContentOut   — GET /api/heritages/{slug}  (heritage + full scenes, one load)
- ModelAssetOut, SkyPresetOut, CameraOut, VoiceClipOut, VoiceOut,
  MediaItemOut, InteractiveHighlightOut, InteractiveOut, SceneHighlightOut
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Leaf schemas (no forward refs) ─────────────────────────────────

class LanguageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class VoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    title: str | None = None
    bio: str | None = None
    headshot_url: str | None = None
    intro_video_url: str | None = None


class ModelAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_url: str
    format: str
    lod_level: int
    compression: str | None = None
    file_size_bytes: int | None = None


class SkyPresetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    turbidity: float | None = None
    rayleigh: float | None = None
    mie_coefficient: float | None = Field(
        default=None, serialization_alias="mieCoefficient"
    )
    mie_directional_g: float | None = Field(
        default=None, serialization_alias="mieDirectionalG"
    )
    elevation: float | None = None
    azimuth: float | None = None
    exposure: float | None = None
    cloud_coverage: float | None = Field(
        default=None, serialization_alias="cloudCoverage"
    )
    cloud_density: float | None = Field(
        default=None, serialization_alias="cloudDensity"
    )
    stars: float | None = None
    light_settings: dict[str, Any] | None = None


class CameraOut(BaseModel):
    """Derived from Scene columns — not a DB table."""
    node_name: str | None = None
    start_position: dict[str, Any] | list[Any] | None = None
    start_target: dict[str, Any] | list[Any] | None = None
    zoom_position: dict[str, Any] | list[Any] | None = None
    zoom_target: dict[str, Any] | list[Any] | None = None
    # GLB chỉ chứa camera + animation clip (không mesh); có thì quỹ đạo camera
    # của cảnh do clip quyết định và seek theo thời gian audio.
    path_url: str | None = None
    instant_move: bool


class VoiceClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_url: str | None = None
    audio_url: str | None = None
    bubble_text: str | None = None
    sort_order: int
    voice: VoiceOut


class MediaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str | None = None
    caption: str | None = None
    asset_url: str
    thumb_url: str | None = None
    credit: str | None = None
    sort_order: int


class InteractiveHighlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    popup_title: str | None = None
    popup_text: str | None = None
    media_url: str | None = None
    cam_pos: dict[str, Any] | list[Any] | None = None
    cam_target: dict[str, Any] | list[Any] | None = None
    lens_pos: dict[str, Any] | list[Any] | None = None
    lens_rot: dict[str, Any] | list[Any] | None = None
    lens_scale: dict[str, Any] | list[Any] | None = None
    sort_order: int


class InteractiveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mode: str
    cam_pos: dict[str, Any] | list[Any] | None = None
    cam_target: dict[str, Any] | list[Any] | None = None
    explore_area: dict[str, Any] | list[Any] | None = None
    explore_title: str | None = None
    explore_description: str | None = None
    highlights: list[InteractiveHighlightOut] = Field(default_factory=list)


class SceneHighlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_url: str
    position: dict[str, Any] | list[Any]
    rotation: dict[str, Any] | list[Any]
    scale: dict[str, Any] | list[Any]
    animation_type: str | None = None


#######################################################################
# Scene detail (full) — becomes "scene" in the FULL single-load payload
#######################################################################

class SceneDetailOut(BaseModel):
    """Full scene payload for the single-load content endpoint."""
    id: int
    slug: str
    title: str
    description: str | None = None
    sequence: int
    sky: SkyPresetOut | None = None
    camera: CameraOut
    voice_clips: list[VoiceClipOut] = Field(default_factory=list)
    models: list[ModelAssetOut] = Field(default_factory=list)
    media: list[MediaItemOut] = Field(default_factory=list)
    interactive: list[InteractiveOut] = Field(default_factory=list)
    highlights: list[SceneHighlightOut] = Field(default_factory=list)


# ── Aggregate schemas ──────────────────────────────────────────────

class HeritageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    tagline: str | None = None
    description: str | None = None
    region: str | None = None
    lat: float | None = None
    lng: float | None = None
    duration_seconds: int | None = None
    launch_date: date | None = None
    publish_state: str
    publish_date: date | None = None
    headline: str | None = None
    map_zoom: float | None = None
    hover_video_url: str | None = None
    community_made: bool
    presented_by_logo_url: str | None = None
    display_map: bool
    splash_image_url: str | None = None
    card_image_url: str | None = None

    language1: LanguageOut | None = None
    language2: LanguageOut | None = None
    voices: list[VoiceOut] = Field(default_factory=list)
    voice_length: int = 0


# ── Aggregate schemas ──────────────────────────────────────────────

class HeritageContentOut(BaseModel):
    """GET /api/heritages/{heritage_slug} — full single-load payload.

    Mirrors CyArk /content/{slug}: heritage + overview (intro scene,
    sequence -1) + voices + full scenes (camera, sky, voice_clips, models,
    media, interactive, highlights).
    """
    heritage: HeritageOut
    overview: SceneDetailOut | None = None
    scenes: list[SceneDetailOut] = Field(default_factory=list)


# ── Tour playback ──────────────────────────────────────────────────
#
# `playback` mirror 1:1 the `playback` map of the Tapestry `tour.json` fixture
# that the frontend player consumes (`features/tour/tour-data.ts` →
# `ScenePlayback`). Field names stay camelCase on purpose: the client reads
# `narrationUrl`, `timedHighlights`, `startSeconds`, ... verbatim.

class TimedHighlightOut(BaseModel):
    """Scene highlight gắn mốc thời gian trên timeline của narration."""

    id: int
    model_url: str
    position: dict[str, Any] | list[Any]
    rotation: dict[str, Any] | list[Any]
    scale: dict[str, Any] | list[Any]
    animation_type: str | None = None
    startSeconds: float = 0.0
    endSeconds: float | None = None


class ScenePlaybackOut(BaseModel):
    """Audio + timing cho một scene, khoá theo scene key ("s0".."sN")."""

    narrationUrl: str | None = None
    captionsUrl: str | None = None
    timedHighlights: list[TimedHighlightOut] = Field(default_factory=list)
    exploreArea: dict[str, Any] | list[Any] | None = None
    exploreTitle: str | None = None
    exploreDescription: str | None = None


class TourContentOut(BaseModel):
    """GET /api/heritages/{heritage_slug}/tour — payload + playback.

    Same shape as the `tour.json` fixture the tour player was built against:
    one request returns the model URL, the full content payload and the
    per-scene audio map.
    """

    modelUrl: str | None = None
    payload: HeritageContentOut
    playback: dict[str, ScenePlaybackOut] = Field(default_factory=dict)


# ── Error schema ───────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail