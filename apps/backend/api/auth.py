"""Authentication API endpoints.

Provides user registration, login, and protected user info endpoints.
Uses JWT tokens for authentication and bcrypt for password hashing.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.models.user import Account, Role, UserConsent, UserProfile
from apps.backend.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    UserMeResponse,
    UserPayload,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


async def get_db() -> AsyncSession:
    """Database session dependency."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Account:
    """Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        Account object of authenticated user
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    account_id = payload.get("sub")
    if account_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Query account with relationships
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.role))
        .where(Account.id == int(account_id))
    )
    account = result.scalar_one_or_none()
    
    if account is None or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không tồn tại hoặc đã bị vô hiệu hóa",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return account


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Register a new user account.
    
    Creates a new account with hashed password, default USER role,
    and initializes profile and consent records.
    """
    try:
        # Check if email or username already exists
        result = await db.execute(
            select(Account).where(
                or_(Account.email == request.email, Account.username == request.username)
            )
        )
        existing_account = result.scalar_one_or_none()
        
        if existing_account:
            if existing_account.email == request.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email đã tồn tại",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username đã tồn tại",
                )
        
        # Get or create USER role (role_id = 1)
        result = await db.execute(select(Role).where(Role.id == 1))
        user_role = result.scalar_one_or_none()
        
        if user_role is None:
            # Create USER role if it doesn't exist
            log.warning("USER role not found, creating it now")
            user_role = Role(id=1, name="USER")
            db.add(user_role)
            await db.flush()
        
        # Hash password
        log.debug(f"Hashing password for user: {request.username}")
        password_hash = hash_password(request.password)
        
        # Create account
        new_account = Account(
            email=request.email,
            username=request.username,
            password_hash=password_hash,
            is_active=True,
            role_id=1,
        )
        db.add(new_account)
        await db.flush()  # CRITICAL: Get account.id before creating related records
        
        log.debug(f"Created account with id={new_account.id}")
        
        # Create default user profile
        profile = UserProfile(
            account_id=new_account.id,
            display_name=request.username,
        )
        db.add(profile)
        
        # Create default user consent
        consent = UserConsent(
            account_id=new_account.id,
            analytics_opt_in=False,
        )
        db.add(consent)
        
        # Commit all changes
        await db.commit()
        
        log.info(f"New user registered successfully: {request.username} (id={new_account.id})")
        
        return RegisterResponse(
            message="Đăng ký thành công",
            account_id=new_account.id,
            email=new_account.email,
            username=new_account.username,
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        await db.rollback()
        raise
        
    except Exception as e:
        # Log unexpected errors and rollback transaction
        await db.rollback()
        log.error(f"Registration failed for {request.username}: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi đăng ký: {str(e)}",
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate user and return JWT token.
    
    Accepts either email or username in the username_or_email field.
    """
    # Query account by email or username
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.role))
        .where(
            or_(
                Account.email == request.username_or_email,
                Account.username == request.username_or_email,
            )
        )
    )
    account = result.scalar_one_or_none()
    
    # Check if account exists and is active
    if account is None or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản hoặc mật khẩu không chính xác",
        )
    
    # Verify password
    if not verify_password(request.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản hoặc mật khẩu không chính xác",
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": str(account.id),
            "email": account.email,
            "username": account.username,
            "role": account.role.name,
        }
    )
    
    log.info(f"User logged in: {account.username} (id={account.id})")
    
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserPayload(
            id=account.id,
            email=account.email,
            username=account.username,
            role=account.role.name,
        ),
    )


@router.get("/me", response_model=UserMeResponse)
async def get_current_user(
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> UserMeResponse:
    """Get current authenticated user's information.
    
    Protected endpoint that requires valid JWT token in Authorization header.
    """
    # Load profile and consent
    result = await db.execute(
        select(Account)
        .options(
            selectinload(Account.role),
            selectinload(Account.profile),
            selectinload(Account.consent),
        )
        .where(Account.id == account.id)
    )
    account = result.scalar_one()
    
    # Build response
    profile_data = None
    if account.profile:
        profile_data = {
            "display_name": account.profile.display_name,
            "avatar_url": account.profile.avatar_url,
            "bio": account.profile.bio,
        }
    
    consent_data = None
    if account.consent:
        consent_data = {
            "analytics_opt_in": account.consent.analytics_opt_in,
        }
    
    return UserMeResponse(
        id=account.id,
        email=account.email,
        username=account.username,
        role=account.role.name,
        is_active=account.is_active,
        profile=profile_data,
        consent=consent_data,
    )
