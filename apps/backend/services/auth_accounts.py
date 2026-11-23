"""Account creation and current account checks shared by authentication routes."""
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import hash_password
from apps.backend.models.admin import AccountRole, AdminAccount


async def find_email(db: AsyncSession, email: str) -> AdminAccount | None:
    rows = (await db.execute(select(AdminAccount).where(func.lower(AdminAccount.email) == email.lower()).limit(2))).scalars().all()
    if len(rows) > 1:
        raise HTTPException(503, "This account needs support before sign-in. Please contact an administrator.")
    return rows[0] if rows else None


def require_available(account: AdminAccount) -> None:
    locked = account.locked_until
    if locked and locked.tzinfo is None:
        locked = locked.replace(tzinfo=timezone.utc)
    if not account.is_active or (locked and locked > datetime.now(timezone.utc)):
        raise HTTPException(403, "This account is locked or not activated. Please contact support.")


async def create_user(db: AsyncSession, *, email: str, username: str, password: str) -> AdminAccount:
    email, username = email.strip().lower(), username.strip()
    if await find_email(db, email):
        raise HTTPException(400, "This email is already in use.")
    if (await db.execute(select(AdminAccount.id).where(AdminAccount.username == username))).first():
        raise HTTPException(400, "This username is already taken.")
    user_roles = (await db.execute(select(AccountRole.id).where(func.lower(AccountRole.name) == "user"))).scalars().all()
    if len(user_roles) != 1:
        raise HTTPException(503, "Registration is temporarily unavailable. Please contact support.")
    # Argon2 must not block the async request loop or hold the allocation lock.
    password_hash = await run_in_threadpool(hash_password, password)
    account_id = None
    if db.get_bind().dialect.name == "postgresql":
        # Older deployed schemas have an integer PK with no sequence. Serialize
        # this legacy allocator against INSERTs without changing schema/data.
        await db.execute(text("LOCK TABLE account IN SHARE ROW EXCLUSIVE MODE"))
        allocator = (await db.execute(text("SELECT pg_get_serial_sequence('account', 'id')"))).scalar()
        if not allocator:
            account_id = (await db.execute(select(func.coalesce(func.max(AdminAccount.id), 0) + 1))).scalar_one()
    account = AdminAccount(email=email, username=username, password_hash=password_hash, role_id=user_roles[0], is_active=True)
    if account_id is not None:
        account.id = account_id
    db.add(account)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # An actual uniqueness conflict may race the preliminary checks.
        if await find_email(db, email):
            raise HTTPException(400, "This email is already in use.") from None
        if (await db.execute(select(AdminAccount.id).where(AdminAccount.username == username))).first():
            raise HTTPException(400, "This username is already taken.") from None
        raise HTTPException(503, "Registration is temporarily unavailable. Please contact support.") from None
    await db.refresh(account)
    return account
