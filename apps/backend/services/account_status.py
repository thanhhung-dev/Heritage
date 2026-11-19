"""Atomic account state transitions and permanent old-session invalidation."""
from fastapi import HTTPException
from sqlalchemy import case, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.models.admin import AdminAccount
from apps.backend.schemas.account_status import AccountStatusOut
from apps.backend.services.account_access import account_by


async def update_account_status(db: AsyncSession, account_id: int, active: bool) -> AccountStatusOut:
    # The expression evaluates the current locked row, making concurrent repeats
    # idempotent. Reactivation never restores the previous credential generation.
    changed = await db.execute(update(AdminAccount).where(AdminAccount.id == account_id).values(
        is_active=active,
        token_version=case(
            (AdminAccount.is_active.is_(True) & (not active), AdminAccount.token_version + 1),
            else_=AdminAccount.token_version,
        ),
    ).returning(AdminAccount.id))
    if changed.scalar_one_or_none() is None:
        raise HTTPException(404, "Account not found.")
    account = await account_by(db, account_id=account_id)
    result = AccountStatusOut(
        account_id=str(account_id), email=account["email"], username=account["username"],
        role=str(account["role"] or "user").lower(), is_active=account["is_active"],
    )
    await db.commit()
    return result
