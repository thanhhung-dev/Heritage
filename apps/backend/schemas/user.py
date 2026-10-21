from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ALLOWED_IMAGE_URL_SCHEMES = {"http", "https"}


def _validate_image_url(value: str | None) -> str | None:
    """Reject non-http(s) URL schemes (e.g. ``javascript:``) for avatar/banner
    URLs, which are rendered directly as ``<img src>``/CSS ``background-image``
    on the profile page. Empty/None values are allowed (clears the field)."""
    if value is None:
        return value
    trimmed = value.strip()
    if not trimmed:
        return None
    parsed = urlparse(trimmed)
    if parsed.scheme.lower() not in _ALLOWED_IMAGE_URL_SCHEMES or not parsed.netloc:
        raise ValueError("URL must be a valid http:// or https:// link.")
    return trimmed


class SocialLinks(BaseModel):
    """Social media handles/URLs shown on the profile."""

    instagram: str | None = None
    linkedin: str | None = None
    twitter: str | None = None


class UserProfileResponse(BaseModel):
    """Clean profile payload matching the FE `ProfileData` shape (no leaked id/account_id)."""

    model_config = ConfigDict(from_attributes=True)

    display_name: str | None = None
    handle: str | None = None
    avatar_url: str | None = None
    banner_url: str | None = None
    bio: str | None = None
    country: str | None = None
    city: str | None = None
    display_email: bool
    joined_at: datetime = Field(validation_alias="created_at", serialization_alias="joined_at")
    socials: SocialLinks | None = None
    total_hours: float
    level: str | None = None
    featured_badges: list[str] | None = None
    show_activity_on_profile: bool


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    handle: str | None = Field(default=None, min_length=1, max_length=50)
    avatar_url: str | None = Field(default=None)
    banner_url: str | None = Field(default=None)
    bio: str | None = Field(default=None)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    display_email: bool | None = Field(default=None)
    socials: SocialLinks | None = Field(default=None)
    featured_badges: list[str] | None = Field(default=None)
    show_activity_on_profile: bool | None = Field(default=None)

    @field_validator("featured_badges")
    @classmethod
    def validate_featured_badges(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(v) > 3:
            raise ValueError("You can feature at most 3 badges.")
        return v

    @field_validator("avatar_url", "banner_url")
    @classmethod
    def validate_image_url(cls, v: str | None) -> str | None:
        return _validate_image_url(v)


class UserConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analytics_opt_in: bool


class UserConsentUpdate(BaseModel):
    analytics_opt_in: bool


class BadgeResponse(BaseModel):
    """A single badge in the Badges grid, merging catalogue + unlock state."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(validation_alias="code", serialization_alias="id")
    title: str
    description: str
    icon_key: str
    is_unlocked: bool
    earned_at: date | None = None


class MilestoneTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(validation_alias="code", serialization_alias="id")
    title: str
    is_completed: bool


class MilestoneLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(validation_alias="code", serialization_alias="id")
    level_name: str
    description: str
    is_unlocked: bool
    tasks: list[MilestoneTaskResponse]
