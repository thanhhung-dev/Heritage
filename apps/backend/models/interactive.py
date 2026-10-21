from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base


class Interactive(Base):
    __tablename__ = "interactive"

    id: Mapped[int] = mapped_column(primary_key=True)

    scene_id: Mapped[int] = mapped_column(
        ForeignKey("scene.id", ondelete="CASCADE"),
        nullable=False,
    )

    mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    cam_pos: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    cam_target: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    explore_area: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Tiêu đề + mô tả hiện trong panel khi vào chế độ đi bộ (`free_explore`).
    # Cột riêng chứ không nhét vào `explore_area`: đây là nội dung biên tập, còn
    # `explore_area` là hình học.
    explore_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    explore_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scene: Mapped["Scene"] = relationship(
        "Scene",
        back_populates="interactives",
    )

    highlights: Mapped[list["InteractiveHighlight"]] = relationship(
        "InteractiveHighlight",
        back_populates="interactive",
        cascade="all, delete-orphan",
    )