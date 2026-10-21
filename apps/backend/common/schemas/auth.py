"""Identity responses shared by sign-in and the current-user endpoint."""
from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User information in responses."""

    account_id: str = Field(..., description="Account UUID")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    role: str = Field(default="user", description="User role")


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str = Field(..., description="Error message")
