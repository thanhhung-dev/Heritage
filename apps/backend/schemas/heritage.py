from datetime import date
from pydantic import BaseModel, ConfigDict


class VoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    title: str | None = None
    bio: str | None = None
    headshot_url: str | None = None
    intro_video_url: str | None = None


class LanguageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


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
    publish_state: int
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
    voices: list[VoiceOut] = []
    voice_length: int = 0