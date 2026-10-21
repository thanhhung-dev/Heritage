from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base


class Scene(Base):
    __tablename__ = "scene"

    id: Mapped[int] = mapped_column(primary_key=True)

    heritage_id: Mapped[int] = mapped_column(
        ForeignKey("heritage.id", ondelete="CASCADE"),
        nullable=False,
    )

    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sky_preset_id: Mapped[int | None] = mapped_column(
        ForeignKey("sky_preset.id", ondelete="SET NULL"),
        nullable=True,
    )

    camera_node_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    cam_start_pos: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    cam_start_target: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    cam_zoom_pos: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    cam_zoom_target: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    instant_move: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    heritage: Mapped["Heritage"] = relationship(
        "Heritage",
        back_populates="scenes",
    )

    sky_preset: Mapped["SkyPreset | None"] = relationship(
        "SkyPreset",
        back_populates="scenes",
    )

    model_assets: Mapped[list["ModelAsset"]] = relationship(
        "ModelAsset",
        back_populates="scene",
        cascade="all, delete-orphan",
    )

    voice_clips: Mapped[list["VoiceClip"]] = relationship(
        "VoiceClip",
        back_populates="scene",
        cascade="all, delete-orphan",
    )

    media_items: Mapped[list["MediaItem"]] = relationship(
        "MediaItem",
        back_populates="scene",
        cascade="all, delete-orphan",
    )

    interactives: Mapped[list["Interactive"]] = relationship(
        "Interactive",
        back_populates="scene",
        cascade="all, delete-orphan",
    )

    scene_highlights: Mapped[list["SceneHighlight"]] = relationship(
        "SceneHighlight",
        back_populates="scene",
        cascade="all, delete-orphan",
    )