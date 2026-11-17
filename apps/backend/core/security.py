"""Shared Argon2 and JWT primitives used by the active authentication API."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30
ph = PasswordHasher()
bearer_scheme = HTTPBearer(auto_error=False)


def signing_key() -> str:
    # Resolve after dotenv has loaded, and never sign with a public fallback.
    key = os.environ.get("JWT_SECRET_KEY", "").strip()
    if not key or key == "your-secret-key-change-this-in-production":
        raise HTTPException(503, "JWT_SECRET_KEY must be configured.")
    return key


def unauthorized(detail: str = "Invalid or expired token.") -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerificationError, InvalidHashError):
        return False


def _encode(data: dict[str, Any], expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {**data, "iat": now, "exp": now + expires_delta, "jti": str(uuid4())}
    for claim, variable in (("iss", "JWT_ISSUER"), ("aud", "JWT_AUDIENCE")):
        if value := os.environ.get(variable, "").strip():
            payload[claim] = value
    return jwt.encode(payload, signing_key(), algorithm=ALGORITHM)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    return _encode(
        {**data, "type": "access"},
        expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def _decode(token: str) -> dict[str, Any]:
    issuer = os.environ.get("JWT_ISSUER", "").strip() or None
    audience = os.environ.get("JWT_AUDIENCE", "").strip() or None
    return jwt.decode(
        token, signing_key(), algorithms=[ALGORITHM], issuer=issuer, audience=audience,
        options={"require": ["exp", "sub"], "verify_aud": audience is not None},
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = _decode(token)
        # Legacy login tokens have no type. Password-reset tokens are never credentials.
        if payload.get("type", "access") != "access" or not payload["sub"]:
            raise unauthorized()
        return payload
    except jwt.InvalidTokenError:
        raise unauthorized() from None


def bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized("Bearer token required.")
    return credentials.credentials


async def get_current_user(token: str = Depends(bearer_token)) -> dict[str, Any]:
    return decode_access_token(token)


def require_admin(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if str(current_user.get("role", "")).lower() != "admin":
        raise HTTPException(403, "Administrator permission required.")
    return current_user


def create_password_reset_token(email: str) -> str:
    return _encode({"sub": email, "type": "reset"}, timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES))


def verify_reset_password_token(token: str) -> str | None:
    try:
        payload = _decode(token)
        return payload["sub"] if payload.get("type") == "reset" else None
    except jwt.InvalidTokenError:
        return None


verify_password_reset_token = verify_reset_password_token
