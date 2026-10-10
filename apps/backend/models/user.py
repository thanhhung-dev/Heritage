from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from apps.backend.db.base import Base

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="role")


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    role_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("roles.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="accounts")
    profile: Mapped[Optional["UserProfile"]] = relationship("UserProfile", back_populates="account", uselist=False, cascade="all, delete-orphan")
    consent: Mapped[Optional["UserConsent"]] = relationship("UserConsent", back_populates="account", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profile"

    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("account.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="profile")


class UserConsent(Base):
    __tablename__ = "user_consent"

    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("account.id", ondelete="CASCADE"), primary_key=True)
    analytics_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="consent")