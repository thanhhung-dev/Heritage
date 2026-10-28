"""Transactional account registration around the existing account schema."""
from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import hash_password
from apps.backend.models.admin import AdminAccount
from apps.backend.schemas.auth import RegisterRequest


class AccountConflict(Exception):
    """A public registration conflict, translated by the HTTP boundary."""


class AccountService:
    def __init__(self, db: AsyncSession):
        self.db = db

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
