from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base


class MediaItem(Base):
    __tablename__ = "media_item"

    id: Mapped[int] = mapped_column(primary_key=True)

    scene_id: Mapped[int] = mapped_column(
        ForeignKey("scene.id", ondelete="CASCADE"),
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    caption: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    asset_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    thumb_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    credit: Mapped[str | None] = mapped_column(
        Text,
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

    scene: Mapped["Scene"] = relationship(
        "Scene",
        back_populates="media_items",
    )