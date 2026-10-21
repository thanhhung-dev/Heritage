from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base


class InteractiveHighlight(Base):
    __tablename__ = "interactive_highlight"

    id: Mapped[int] = mapped_column(primary_key=True)

    interactive_id: Mapped[int] = mapped_column(
        ForeignKey("interactive.id", ondelete="CASCADE"),
        nullable=False,
    )

    popup_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    popup_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    media_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    cam_pos: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    cam_target: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    lens_pos: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    lens_rot: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    lens_scale: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    interactive: Mapped["Interactive"] = relationship(
        "Interactive",
        back_populates="highlights",
    )
