"""Security utilities for password hashing and JWT token management."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes

# Password hasher using argon2id
ph = PasswordHasher()

# HTTP Bearer scheme for JWT
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using argon2id.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Dictionary of decoded claims
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials with JWT token
        
    Returns:
        Dictionary containing user information from token
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    # Verify required claims
    account_id = payload.get("sub")
    if account_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload

def require_admin(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Allow only accounts carrying the ADMIN role claim."""
    if str(current_user.get("role", "")).lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền quản trị.",
        )
    return current_user


def create_password_reset_token(email: str) -> str:
    """Create a JWT token for password reset.

    Args:
        email: Email address to encode in the token's `sub` claim.

    Returns:
        Encoded JWT token string for password reset, valid for
        PASSWORD_RESET_TOKEN_EXPIRE_MINUTES minutes. Uses an explicit
        UTC-aware timestamp (`datetime.now(timezone.utc)`) when computing
        the expiration so verification is not affected by the server's
        local timezone.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": email,
        "type": "reset",
        "exp": expire,
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_reset_password_token(token: str) -> str | None:
    """Verify a password reset token and extract the email.

    Args:
        token: JWT token string to verify.

    Returns:
        Email address (the `sub` claim) if the token is valid and not
        expired, or None if the token is invalid, malformed, of the
        wrong type, or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify token type
        if payload.get("type") != "reset":
            return None

        email = payload.get("sub")
        if email is None:
            return None

        return email
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# Backward-compatible alias (previous name used elsewhere in the codebase)
verify_password_reset_token = verify_reset_password_token

