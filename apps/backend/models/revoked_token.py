"""Persistent per-credential revocation; raw bearer tokens are never stored."""
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.db.base import Base


class RevokedToken(Base):
    __tablename__ = "revoked_access_token"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_revoked_access_token_expires_at", "expires_at"),)
