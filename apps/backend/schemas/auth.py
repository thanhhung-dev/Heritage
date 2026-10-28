"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    
    email: EmailStr = Field(..., description="Email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v


class LoginRequest(BaseModel):
    """Request schema for email/password login."""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    """User information in responses."""
    
    account_id: str = Field(..., description="Account ID serialized as a string")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    role: str = Field(default="user", description="User role")


class RegisterResponse(BaseModel):
    """Response schema for successful registration."""
    
    account_id: str = Field(..., description="Account ID serialized as a string")
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    message: str = Field(default="Registration successful", description="Success message")


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


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    detail: str = Field(..., description="Error message")


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password."""
    
    email: EmailStr = Field(..., description="Email address")


class ResetPasswordRequest(BaseModel):
    """Request schema for reset password."""
    
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=12, description="New password (minimum 12 characters)")
    
    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Validate password complexity."""
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError("Password must include uppercase, lowercase, number, and special characters")
        
        return v
