from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    avatar_url: str | None = Field(default=None)
    bio: str | None = Field(default=None)


class UserConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    analytics_opt_in: bool


class UserConsentUpdate(BaseModel):
    analytics_opt_in: bool
