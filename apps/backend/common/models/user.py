"""User authentication and profile models.

Database tables for user accounts, roles, profiles, and consent settings.
Supports JWT-based authentication with bcrypt password hashing.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.common.db.base import Base, TimestampMixin


class Role(Base):
    """User roles (USER, ADMIN, etc.)."""
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    # Relationships
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="role")


class Account(Base, TimestampMixin):
    """User account table with authentication credentials."""
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False, comment="bcrypt hash")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("role.id", ondelete="RESTRICT"), nullable=False, default=1)
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)
    
    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="accounts")
    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="account", uselist=False, cascade="all, delete-orphan")
    consent: Mapped["UserConsent"] = relationship("UserConsent", back_populates="account", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base, TimestampMixin):
    """User profile information."""
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("account.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="profile")


class UserConsent(Base, TimestampMixin):
    """User consent and privacy settings."""
    __tablename__ = "user_consent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("account.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    analytics_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    
    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="consent")
