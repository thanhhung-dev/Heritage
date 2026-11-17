"""Admin sign-in and sign-out business logic using existing identity storage."""
import secrets
from datetime import timedelta

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import create_access_token, hash_password, unauthorized, verify_password
from apps.backend.schemas.auth import LoginRequest, LoginResponse, UserResponse
from apps.backend.services.account_access import account_by, authorize_admin, is_available, require_admin_role
from apps.backend.services.token_revocation import revoke_token

_dummy_hash = hash_password(secrets.token_urlsafe(32))
ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES = 60


async def login_admin(db: AsyncSession, request: LoginRequest) -> LoginResponse:
    account = await account_by(db, email=str(request.email).strip().lower())
    valid = await run_in_threadpool(
        verify_password, request.password, account["password_hash"] if account else _dummy_hash,
    )
    if not valid or not is_available(account):
        raise unauthorized("Incorrect email or password.")
    require_admin_role(account)
    user = UserResponse(
        account_id=str(account["id"]), email=account["email"],
        username=account["username"], role="admin",
    )
    token = create_access_token(
        {"sub": user.account_id, "email": user.email, "username": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return LoginResponse(access_token=token, token_type="bearer", user=user)


async def logout_admin(db: AsyncSession, token: str, payload: dict) -> None:
    # Do not reject an already revoked token here: retries must be safe.
    await authorize_admin(db, payload)
    await revoke_token(db, token, payload["exp"])
