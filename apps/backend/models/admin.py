from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.db.base import Base, TimestampMixin

def _uuid_pk():
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


class AccountRole(Base):
    """Role lookup used by the current account/auth compatibility model."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class AdminAccount(Base, TimestampMixin):
    """Compatibility name for the legacy auth API; storage is ``account``."""

    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey(AccountRole.id, ondelete="RESTRICT"), nullable=True
    )
