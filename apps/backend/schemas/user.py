from pydantic import BaseModel, ConfigDict


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


class UserConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analytics_opt_in: bool


class UserConsentUpdate(BaseModel):
    analytics_opt_in: bool
