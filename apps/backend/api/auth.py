"""Authentication API endpoints for user registration and login."""

from __future__ import annotations

import logging
import os
import secrets
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from apps.backend.core.security import (
    create_access_token,
    create_password_reset_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_reset_password_token,
)
from apps.backend.core.email import send_reset_password_email
from apps.backend.core import security as auth_security
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.models.admin import AdminAccount
from apps.backend.services.auth_accounts import create_user, find_email, require_available
from apps.backend.schemas.auth import (
    ErrorResponse,
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    UserResponse,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


async def get_db() -> AsyncSession:
    """Database session dependency."""
    if AsyncSessionLocal.kw.get("bind") is None:
        raise HTTPException(503, "Authentication is temporarily unavailable. Please try again later.")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            log.warning("auth_database_unavailable")
            raise HTTPException(503, "Authentication is temporarily unavailable. Please try again later.") from None


def require_signing_config() -> None:
    if not auth_security.SECRET_KEY or auth_security.SECRET_KEY == "your-secret-key-change-this-in-production":
        raise HTTPException(503, "Sign-in is temporarily unavailable. Please contact support.")

async def role_name(db: AsyncSession, role_id: int | None) -> str:
    result = await db.execute(
        text("SELECT name FROM roles WHERE id = :role_id"),
        {"role_id": role_id},
    )
    return (result.scalar_one_or_none() or "USER").lower()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Email or username already exists"},
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
    new_account = await create_user(db, email=str(request.email), username=request.username, password=request.password)
    
    log.info("auth_account_registered", extra={"account_id": new_account.id})
    
    return RegisterResponse(
        account_id=str(new_account.id),
        email=new_account.email,
        username=new_account.username,
        message="Registration successful",
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid login credentials"},
    },
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Đăng nhập bằng email và mật khẩu."""
    email = request.email.strip().lower()
    account = await find_email(db, email)

    if not account or not await run_in_threadpool(verify_password, request.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    require_available(account)
    require_signing_config()

    await db.commit()

    # Create access token
    role = await role_name(db, account.role_id)
    access_token = create_access_token(
        data={
            "sub": str(account.id),
            "email": account.email,
            "username": account.username,
            "role": role,
        }
    )
    
    log.info(f"User logged in: {account.email} (username={account.username}, id={account.id})")
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            account_id=str(account.id),
            email=account.email,
            username=account.username,
            role=role,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not signed in or invalid token"},
    },
)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Lấy thông tin người dùng hiện tại.
    
    Args:
        current_user: User information from JWT token
        
    Returns:
        UserResponse: Thông tin người dùng
    """
    try:
        actor = int(current_user["sub"])
        if actor <= 0 or actor >= 2**63 or current_user.get("type") not in {None, "access"}:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise HTTPException(401, "Invalid sign-in session.") from None
    account = await db.get(AdminAccount, actor)
    if account is None:
        raise HTTPException(401, "This sign-in session is no longer available.")
    require_available(account)
    return UserResponse(account_id=str(account.id), email=account.email, username=account.username,
                        role=await role_name(db, account.role_id))


@router.post(
    "/google",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid Google ID token"},
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
    require_signing_config()
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(503, "Google sign-in is not available. Use email and password instead.")
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
                    detail="Invalid Google ID token.",
                )
            
            token_info = response.json()
            if not isinstance(token_info, dict) or token_info.get("aud") != client_id:
                raise HTTPException(401, "Invalid Google ID token audience.")
            
            # Validate required fields
            email = token_info.get("email")
            if not isinstance(email, str) or not email.strip():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not retrieve an email from Google.",
                )
            
            # Check if email is verified
            if token_info.get("email_verified") not in (True, "true"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Your Google email is not verified.",
                )
            
    except (httpx.RequestError, ValueError):
        log.warning("google_verification_unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Google for verification.",
        )
    
    # Find or create account
    email = email.strip().lower()
    account = await find_email(db, email)
    
    if not account:
        # A random suffix avoids collisions between equal email local-parts.
        username = "google_" + secrets.token_hex(12)
        try:
            account = await create_user(db, email=email, username=username, password=secrets.token_urlsafe(32))
        except HTTPException as error:
            if error.status_code != 400:
                raise
            account = await find_email(db, email)
            if account is None:
                raise
    require_available(account)
    
    await db.commit()

    role = await role_name(db, account.role_id)
    access_token = create_access_token(
        data={
            "sub": str(account.id),
            "email": account.email,
            "username": account.username,
            "role": role,
            "auth_method": "google",
        }
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            account_id=str(account.id),
            email=account.email,
            username=account.username,
            role=role,
        ),
    )


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Password reset instructions sent"},
        404: {"model": ErrorResponse, "description": "Email is not registered"},
    },
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Yêu cầu khôi phục mật khẩu qua email.
    
    Args:
        request: Email để nhận link khôi phục
        db: Database session
        
    Returns:
        Message thông báo đã gửi email
        
    Raises:
        HTTPException 404: Nếu email không tồn tại trong hệ thống
        
    Note:
        Theo yêu cầu UX-first approach: trả về lỗi cụ thể khi email không tồn tại
        để người dùng biết và có thể đăng ký tài khoản mới.
    """
    # Find account by email
    result = await db.execute(
        select(AdminAccount).where(AdminAccount.email == request.email)
    )
    account = result.scalar_one_or_none()
    
    # Return 404 if email not found (UX-first approach)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This email is not registered.",
        )
    
    # Generate reset token (valid for 30 minutes), encoding the account's
    # email in the `sub` claim.
    reset_token = create_password_reset_token(account.email)
    
    # Get frontend base URL from settings
    frontend_url = "http://localhost:3000"  # Default fallback
    
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    
    # Send the email to the exact address the account registered with.
    # The SMTP call is blocking, so it's offloaded to a worker thread via
    # run_in_threadpool to avoid freezing the async event loop. If SMTP is
    # not configured (or the send fails), the link is simply logged to the
    # console instead of raising - the dev flow keeps working either way.
    try:
        email_sent = await run_in_threadpool(
            send_reset_password_email,
            account.email,
            reset_link,
            account.username,
        )
    except Exception:
        log.exception("Unexpected error while sending password reset email to %s", account.email)
        email_sent = False
    
    if email_sent:
        log.info(f"Password reset email sent to: {account.email}")
    else:
        # Fallback: Print link to console (dev mode / SMTP not configured)
        log.info(f"Password reset requested for: {account.email}")
        log.info(f"Reset link (copy to browser): {reset_link}")
        print(f"\n{'='*80}")
        print(f"PASSWORD RESET LINK FOR: {account.email}")
        print(f"{reset_link}")
        print(f"{'='*80}\n")
    
    return {
        "message": "Password reset instructions have been sent to your email. Please check your inbox."
    }


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired token"},
    },
)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Đặt lại mật khẩu với token hợp lệ.
    
    Args:
        request: Token và mật khẩu mới
        db: Database session
        
    Returns:
        Message thông báo đặt lại mật khẩu thành công
        
    Raises:
        HTTPException 400: Nếu token không hợp lệ hoặc đã hết hạn
    """
    # Decode the reset token to retrieve the email it was issued for.
    email = verify_reset_password_token(request.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired.",
        )
    
    # Find account by email
    result = await db.execute(
        select(AdminAccount).where(AdminAccount.email == email)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account does not exist.",
        )
    
    # Hash new password and persist it to PostgreSQL
    new_password_hash = hash_password(request.new_password)
    account.password_hash = new_password_hash
    await db.commit()
    
    log.info(f"Password reset successfully for: {email}")
    
    return {
        "message": "Password reset successful."
    }


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
