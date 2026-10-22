"""User profile, consent, and gamification models.

Database tables for user profiles, consent settings, badges, and milestones.
Identity is owned by `AdminAccount` (apps.backend.models.admin); these tables
reference it via its UUID primary key — there is no separate `account`/`role`
table in this application.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base, TimestampMixin


class UserProfile(Base, TimestampMixin):
    """User profile information shown on the Profile page."""
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("admin_account.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    handle: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    banner_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    socials: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    featured_badges: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    show_activity_on_profile: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    total_hours: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    level: Mapped[str | None] = mapped_column(String(50), nullable=True)


class UserConsent(Base, TimestampMixin):
    """User consent and privacy settings."""
    __tablename__ = "user_consent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("account.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    analytics_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class BadgeDefinition(Base):
    """Catalogue of collectible gamification badges (seeded, not user-editable)."""
    __tablename__ = "badge_definition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon_key: Mapped[str] = mapped_column(String(50), nullable=False, comment="Maps to a FE icon component name")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class UserBadge(Base):
    """A badge unlocked by a specific account."""
    __tablename__ = "user_badge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("account.id", ondelete="CASCADE"), nullable=False, index=True
    )
    badge_id: Mapped[int] = mapped_column(Integer, ForeignKey("badge_definition.id", ondelete="CASCADE"), nullable=False, index=True)
    earned_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class MilestoneLevelDefinition(Base):
    """Catalogue of gamification milestone levels (seeded, not user-editable)."""
    __tablename__ = "milestone_level_definition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    level_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # Relationships
    tasks: Mapped[list["MilestoneTaskDefinition"]] = relationship(
        "MilestoneTaskDefinition", back_populates="level", order_by="MilestoneTaskDefinition.sort_order"
    )


class MilestoneTaskDefinition(Base):
    """A single checklist task belonging to a milestone level (seeded)."""
    __tablename__ = "milestone_task_definition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("milestone_level_definition.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # Relationships
    level: Mapped["MilestoneLevelDefinition"] = relationship("MilestoneLevelDefinition", back_populates="tasks")


class UserMilestoneTask(Base):
    """Completion record of a milestone task for a specific account."""
    __tablename__ = "user_milestone_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("account.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("milestone_task_definition.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")

