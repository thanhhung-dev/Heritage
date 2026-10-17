"""Security utilities for authentication and authorization.

Provides password hashing with bcrypt and JWT token management.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

# JWT configuration
SECRET_KEY = "heritage-capstone-secret-key-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Bcrypt hashed password string
        
    Note:
        Bcrypt has a maximum password length of 72 bytes.
        Passwords longer than this are truncated automatically.
    """
    # Convert password to UTF-8 bytes
    pwd_bytes = password.encode('utf-8')
    
    # Bcrypt limitation: maximum 72 bytes
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]
    
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    
    # Return as UTF-8 string
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        # Convert plain password to UTF-8 bytes
        pwd_bytes = plain_password.encode('utf-8')
        
        # Truncate to 72 bytes (bcrypt limitation)
        if len(pwd_bytes) > 72:
            pwd_bytes = pwd_bytes[:72]
        
        # Convert hashed password to bytes
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Verify password
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
        
    except Exception:
        # Return False if any error occurs during verification
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a JWT token.
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Decoded token payload if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
