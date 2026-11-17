"""Database-backed revocation shared by all authenticated endpoints."""
from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.models.revoked_token import RevokedToken


def token_digest(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


async def is_revoked(db: AsyncSession, token: str) -> bool:
    return (await db.execute(
        select(RevokedToken.token_hash).where(RevokedToken.token_hash == token_digest(token))
    )).scalar_one_or_none() is not None


async def revoke_token(db: AsyncSession, token: str, expires_at: int) -> None:
    # Atomic, idempotent even when two workers receive logout concurrently.
    await db.execute(insert(RevokedToken).values(
        token_hash=token_digest(token),
        expires_at=datetime.fromtimestamp(expires_at, timezone.utc),
    ).on_conflict_do_nothing(index_elements=[RevokedToken.token_hash]))
    await db.commit()
