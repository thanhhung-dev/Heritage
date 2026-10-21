"""Authentication API endpoints for user registration and login."""

from __future__ import annotations

import logging
import secrets
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.common.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from apps.backend.common.db.base import AsyncSessionLocal
from apps.backend.common.models.admin import AdminAccount
from apps.backend.common.schemas.auth import ErrorResponse, UserResponse
from apps.backend.api.public.auth.schemas import (
    GoogleAuthRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


async def get_db() -> AsyncSession:
    """Database session dependency."""
    async with AsyncSessionLocal() as session:
        yield session


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Email hoặc username đã tồn tại"},
    },
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Đăng ký tài khoản mới.
    
    Args:
        request: Thông tin đăng ký (email, username, password)
        db: Database session
        
    Returns:
        RegisterResponse: Thông tin tài khoản đã tạo
        
    Raises:
        HTTPException 400: Nếu email hoặc username đã tồn tại
    """
    # Check if email already exists
    result = await db.execute(
        select(AdminAccount).where(AdminAccount.username == request.email)
    )
    existing_email = result.scalar_one_or_none()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng",
        )
    
    # Check if username already exists
    result = await db.execute(
        select(AdminAccount).where(AdminAccount.username == request.username)
    )
    existing_username = result.scalar_one_or_none()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username đã được sử dụng",
        )
    
    # Hash password
    password_hash = hash_password(request.password)
    
    # Create new account
    new_account = AdminAccount(
        username=request.username,
        password_hash=password_hash,
    )
    
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    
    log.info(f"New account registered: {new_account.username} (id={new_account.id})")
    
    return RegisterResponse(
        account_id=str(new_account.id),
        email=request.email,
        username=new_account.username,
        message="Đăng ký thành công",
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Thông tin đăng nhập không đúng"},
    },
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Đăng nhập vào hệ thống.
    
    Supports login with username OR email (stored in username field).
    
    Args:
        request: Thông tin đăng nhập (username_or_email, password)
        db: Database session
        
    Returns:
        LoginResponse: Access token và thông tin người dùng
        
    Raises:
        HTTPException 401: Nếu thông tin đăng nhập không đúng
    """
    # Find user by username/email (currently stored in username field)
    result = await db.execute(
        select(AdminAccount).where(
            AdminAccount.username == request.username_or_email
        )
    )
    account = result.scalar_one_or_none()
    
    # Verify password
    if not account or not verify_password(request.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng",
        )
    
    # Check if account is active
    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản đã bị vô hiệu hóa",
        )
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(account.id),
            "username": account.username,
            "role": "admin",  # Default role for now
        }
    )
    
    log.info(f"User logged in: {account.username} (id={account.id})")
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            account_id=str(account.id),
            email=account.username,  # Using username as email for now
            username=account.username,
            role="admin",
        ),
    )


@router.post(
    "/google",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Google ID token không hợp lệ"},
    },
)
async def google_auth(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Đăng nhập hoặc đăng ký bằng Google OAuth 2.0.
    
    Args:
        request: Google ID token từ OAuth flow
        db: Database session
        
    Returns:
        LoginResponse: Access token và thông tin người dùng
        
    Raises:
        HTTPException 401: Nếu Google ID token không hợp lệ
    """
    # Verify Google ID token
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={request.id_token}",
                timeout=10.0,
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google ID token không hợp lệ",
                )
            
            token_info = response.json()
            
            # Validate required fields
            email = token_info.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Không thể lấy email từ Google",
                )
            
            # Check if email is verified
            if not token_info.get("email_verified"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email chưa được xác thực bởi Google",
                )
            
    except httpx.RequestError as e:
        log.error(f"Failed to verify Google token: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể kết nối đến Google để xác thực",
        )
    
    # Find or create account
    result = await db.execute(
        select(AdminAccount).where(AdminAccount.username == email)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        # Create new account for Google user
        # Generate a random password hash (user won't use it for Google login)
        random_password = secrets.token_urlsafe(32)
        password_hash = hash_password(random_password)
        
        account = AdminAccount(
            username=email,
            password_hash=password_hash,
            is_active=True,
        )
        
        db.add(account)
        await db.commit()
        await db.refresh(account)
        
        log.info(f"New Google account created: {email} (id={account.id})")
    else:
        # Check if existing account is active
        if not account.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản đã bị vô hiệu hóa",
            )
        
        log.info(f"Existing Google account logged in: {email} (id={account.id})")
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(account.id),
            "username": account.username,
            "role": "admin",
            "auth_method": "google",
        }
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            account_id=str(account.id),
            email=account.username,
            username=account.username,
            role="admin",
        ),
    )


# Disable Facebook temporarily - localhost domain issues
# @router.post(
#     "/facebook",
#     response_model=LoginResponse,
#     responses={
#         401: {"model": ErrorResponse, "description": "Facebook access token không hợp lệ"},
#     },
# )
# async def facebook_auth(
#     request: FacebookAuthRequest,
#     db: AsyncSession = Depends(get_db),
# ) -> LoginResponse:
#     """Đăng nhập hoặc đăng ký bằng Facebook OAuth 2.0."""
#     pass
