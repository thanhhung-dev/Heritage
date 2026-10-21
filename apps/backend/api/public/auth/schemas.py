"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from apps.backend.common.schemas.auth import UserResponse


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    
    email: EmailStr = Field(..., description="Email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v


class LoginRequest(BaseModel):
    """Request schema for user login."""
    
    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., description="Password")


class RegisterResponse(BaseModel):
    """Response schema for successful registration."""
    
    account_id: str = Field(..., description="Account UUID")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    message: str = Field(default="Đăng ký thành công", description="Success message")


class LoginResponse(BaseModel):
    """Response schema for successful login."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="User information")


class GoogleAuthRequest(BaseModel):
    """Request schema for Google OAuth authentication."""
    
    id_token: str = Field(..., description="Google ID token from OAuth flow")


class FacebookAuthRequest(BaseModel):
    """Request schema for Facebook OAuth authentication."""
    
    access_token: str = Field(..., description="Facebook access token from OAuth flow")
