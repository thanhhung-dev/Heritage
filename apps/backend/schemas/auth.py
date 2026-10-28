"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, TypeAdapter, field_validator, model_validator


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    
    email: EmailStr = Field(..., description="Email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=1024, description="Password (8 to 1024 characters)")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must contain a non-whitespace character")
        return value
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v


class LoginRequest(BaseModel):
    """Accept one login identifier, preserving existing email clients."""

    email: EmailStr | None = Field(default=None, description="Email address")
    username: str | None = Field(default=None, min_length=3, max_length=50)
    username_or_email: str | None = Field(default=None, min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=1024, description="Password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None

    @field_validator("username", "username_or_email")
    @classmethod
    def validate_identifier(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        if info.field_name == "username_or_email" and "@" in value:
            return TypeAdapter(EmailStr).validate_python(value).lower()
        if len(value) > 50 or not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return value

    @model_validator(mode="after")
    def require_one_identifier(self):
        if sum(value is not None for value in (self.email, self.username, self.username_or_email)) != 1:
            raise ValueError("Provide exactly one of email, username or username_or_email")
        return self

    @property
    def identifier(self) -> str:
        return self.email or self.username or self.username_or_email or ""

    @property
    def uses_email(self) -> bool:
        return self.email is not None or (self.username_or_email is not None and "@" in self.username_or_email)


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
