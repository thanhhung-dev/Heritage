"""Resolve current admin permission from the active account/roles schema."""
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def account_by(db: AsyncSession, *, email: str | None = None, account_id: int | None = None):
    condition = "a.email = :email" if email is not None else "a.id = :account_id"
    result = await db.execute(text(
        "SELECT a.id, a.email, a.username, a.password_hash, a.is_active, "
        "a.locked_until, a.token_version, r.name AS role FROM account a "
        "LEFT JOIN roles r ON r.id = a.role_id WHERE " + condition
    ), {"email": email, "account_id": account_id})
    return result.mappings().one_or_none()


def is_available(account) -> bool:
    if not account or not account["is_active"]:
        return False
    locked_until = account["locked_until"]
    if isinstance(locked_until, str):
        locked_until = datetime.fromisoformat(locked_until)
    if locked_until is not None:
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > datetime.now(timezone.utc):
            return False
    return True


def require_admin_role(account) -> None:
    if str(account["role"] or "").lower() != "admin":
        raise HTTPException(403, "Administrator permission required.")


async def authorize_account(db: AsyncSession, payload: dict[str, Any]):
    try:
        account_id = int(payload["sub"])
        if not 0 < account_id < 2**63:
            raise ValueError
    except (KeyError, ValueError, TypeError):
        raise HTTPException(401, "Invalid account.", headers={"WWW-Authenticate": "Bearer"}) from None
    account = await account_by(db, account_id=account_id)
    if not is_available(account):
        raise HTTPException(401, "Account unavailable.", headers={"WWW-Authenticate": "Bearer"})
    version = payload.get("ver", 0)
    if type(version) is not int or version != account["token_version"]:
        raise HTTPException(401, "Session invalidated.", headers={"WWW-Authenticate": "Bearer"})
    return account


async def authorize_admin(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    account = await authorize_account(db, payload)
    require_admin_role(account)
    return {**payload, "email": account["email"], "username": account["username"], "role": "admin"}
