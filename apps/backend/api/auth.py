"""Authentication API endpoints for user registration and login."""

from __future__ import annotations

import logging
import secrets
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import (
    create_access_token,
    create_password_reset_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_reset_password_token,
)
from apps.backend.core.email import send_reset_password_email
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.models.admin import AdminAccount
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
from apps.backend.services.accounts import AccountConflict, AccountService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


async def get_db() -> AsyncSession:
    """Database session dependency."""
    async with AsyncSessionLocal() as session:
        yield session

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
    try:
        new_account = await AccountService(db).register(request)
    except AccountConflict as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except Exception:
        log.exception("Account registration failed")
        raise HTTPException(status_code=500, detail="Registration is temporarily unavailable. Please try again.") from None
    
    log.info(f"New account registered: {new_account.email} (username={new_account.username}, id={new_account.id})")
    
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
    result = await db.execute(
        select(AdminAccount).where(AdminAccount.email == email)
    )
    account = result.scalar_one_or_none()

    if not account or not verify_password(request.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is locked or not activated.",
        )

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
) -> UserResponse:
    """Lấy thông tin người dùng hiện tại.
    
    Args:
        current_user: User information from JWT token
        
    Returns:
        UserResponse: Thông tin người dùng
    """
    return UserResponse(
        account_id=current_user["sub"],
        email=current_user.get("email", ""),
        username=current_user.get("username", ""),
        role=current_user.get("role", "user"),
    )


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
            
            # Validate required fields
            email = token_info.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not retrieve an email from Google.",
                )
            
            # Check if email is verified
            if not token_info.get("email_verified"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Your Google email is not verified.",
                )
            
    except httpx.RequestError as e:
        log.error(f"Failed to verify Google token: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Google for verification.",
        )
    
    # Find or create account
    result = await db.execute(
        select(AdminAccount).where(AdminAccount.email == email)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        # Create new account for Google user
        # Generate a random password hash (user won't use it for Google login)
        random_password = secrets.token_urlsafe(32)
        password_hash = hash_password(random_password)
        
        account = AdminAccount(
            email=email,
            username=email.split('@')[0],  # Use email prefix as username
            password_hash=password_hash,
            is_active=True,
            role_id=1,
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
                detail="This account has been disabled.",
            )
        
        log.info(f"Existing Google account logged in: {email} (id={account.id})")
    
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
