"""Pydantic schemas for authentication API.

Request/response models for registration, login, and user info endpoints.
"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Request body for user registration."""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=6, description="Plain text password (will be hashed)")
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v


class LoginRequest(BaseModel):
    """Request body for user login."""
    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., description="Plain text password")


class UserPayload(BaseModel):
    """User information payload in auth responses."""
    id: int
    email: str
    username: str
    role: str


class AuthResponse(BaseModel):
    """Response body for successful authentication."""
    access_token: str
    token_type: str = "bearer"
    user: UserPayload


class RegisterResponse(BaseModel):
    """Response body for successful registration."""
    message: str
    account_id: int
    email: str
    username: str


class UserMeResponse(BaseModel):
    """Response body for GET /api/auth/me endpoint."""
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    profile: dict | None = None
    consent: dict | None = None
