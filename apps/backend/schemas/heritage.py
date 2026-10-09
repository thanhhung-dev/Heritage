"""Pydantic v2 response schemas for Heritage public API (Story 4).

Contracts:
- HeritageOut          — homepage list + content overview
- SceneOut             — scene summary in content overview
- HeritageContentOut   — GET /api/heritage/{slug}
- SceneDetailOut       — GET /api/heritage/{slug}/scenes/{scene_key}
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
    elevation: float | None = None
    azimuth: float | None = None
    exposure: float | None = None
    light_settings: dict[str, Any] | None = None


class CameraOut(BaseModel):
    """Derived from Scene columns — not a DB table."""
    node_name: str | None = None
    start_position: dict[str, Any] | list[Any] | None = None
    start_target: dict[str, Any] | list[Any] | None = None
    zoom_position: dict[str, Any] | list[Any] | None = None
    zoom_target: dict[str, Any] | list[Any] | None = None
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
    highlights: list[InteractiveHighlightOut] = Field(default_factory=list)


class SceneHighlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_url: str
    position: dict[str, Any] | list[Any]
    rotation: dict[str, Any] | list[Any]
    scale: dict[str, Any] | list[Any]
    animation_type: str | None = None


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


class SceneOut(BaseModel):
    """Scene summary used in content overview. `slug` is derived from `sequence`."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str  # derived: f"s{sequence + 1}"
    title: str
    description: str | None = None
    sequence: int


class HeritageContentOut(BaseModel):
    """GET /api/heritage/{heritage_slug}"""
    heritage: HeritageOut
    scenes: list[SceneOut] = Field(default_factory=list)


class SceneDetailOut(BaseModel):
    """GET /api/heritage/{heritage_slug}/scenes/{scene_key}"""
    heritage: HeritageOut
    scene: SceneOut
    models: list[ModelAssetOut] = Field(default_factory=list)
    sky: SkyPresetOut | None = None
    camera: CameraOut
    voices: list[VoiceClipOut] = Field(default_factory=list)
    media: list[MediaItemOut] = Field(default_factory=list)
    interactive: list[InteractiveOut] = Field(default_factory=list)
    highlights: list[SceneHighlightOut] = Field(default_factory=list)


# ── Error schema ───────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail