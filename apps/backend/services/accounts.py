"""Transactional account registration around the existing account schema."""
from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import hash_password, verify_password
from apps.backend.models.admin import AdminAccount
from apps.backend.schemas.auth import LoginRequest, RegisterRequest


class AccountConflict(Exception):
    """A public registration conflict, translated by the HTTP boundary."""


class InvalidCredentials(Exception):
    pass


class AccountUnavailable(Exception):
    pass


class AccountService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, request: LoginRequest) -> AdminAccount:
        identifier = request.identifier
        predicate = (
            func.lower(AdminAccount.email) == identifier
            if request.uses_email else AdminAccount.username == identifier
        )
        result = await self.db.execute(select(AdminAccount).where(predicate))
        account = result.scalar_one_or_none()
        if account is None or not await asyncio.to_thread(verify_password, request.password, account.password_hash):
            raise InvalidCredentials("Incorrect email or password.")
        is_locked = False
        if account.locked_until is not None:
            # locked_until is a timestamp WITHOUT time zone in the existing
            # schema. PostgreSQL must interpret it using its own session zone;
            # assigning UTC in Python incorrectly extends a local lock by hours.
            locked = await self.db.execute(select(AdminAccount.id).where(
                AdminAccount.id == account.id, AdminAccount.locked_until > func.current_timestamp(),
            ))
            is_locked = locked.scalar_one_or_none() is not None
        if not account.is_active or is_locked:
            raise AccountUnavailable("This account is locked or not activated.")
        return account

    async def check_available(self, email: str, username: str) -> None:
        existing_email = await self.db.execute(
            select(AdminAccount.id).where(func.lower(AdminAccount.email) == email)
        )
        if existing_email.scalar_one_or_none() is not None:
            raise AccountConflict("This email is already in use.")
        existing_username = await self.db.execute(
            select(AdminAccount.id).where(AdminAccount.username == username)
        )
        if existing_username.scalar_one_or_none() is not None:
            raise AccountConflict("This username is already taken.")

    async def register(self, request: RegisterRequest) -> AdminAccount:
        try:
            await self.check_available(request.email, request.username)
            account = AdminAccount(
                email=request.email, username=request.username,
                password_hash=await asyncio.to_thread(hash_password, request.password),
                role_id=1, is_active=True,
            )
            self.db.add(account)
            # PostgreSQL's sequence allocates IDs safely for concurrent requests.
            await self.db.flush()
            await self.db.commit()
            return account
        except IntegrityError:
            # A competing registration may win after the availability checks.
            await self.db.rollback()
            await self.check_available(request.email, request.username)
            raise
        except BaseException:
            await self.db.rollback()
            raise
