from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base


class SceneHighlight(Base):
    __tablename__ = "scene_highlight"

    id: Mapped[int] = mapped_column(primary_key=True)

    scene_id: Mapped[int] = mapped_column(
        ForeignKey("scene.id", ondelete="CASCADE"),
        nullable=False,
    )

    model_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    position: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    rotation: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    scale: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    animation_type: Mapped[str | None] = mapped_column(
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
        back_populates="scene_highlights",
    )