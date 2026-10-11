from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base


class VoiceClip(Base):
    __tablename__ = "voice_clip"

    id: Mapped[int] = mapped_column(primary_key=True)

    voice_id: Mapped[int] = mapped_column(
        ForeignKey("voice.id", ondelete="CASCADE"),
        nullable=False,
    )

    scene_id: Mapped[int] = mapped_column(
        ForeignKey("scene.id", ondelete="CASCADE"),
        nullable=False,
    )

    video_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    audio_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    bubble_text: Mapped[str | None] = mapped_column(
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

    voice: Mapped["Voice"] = relationship(
        "Voice",
        back_populates="voice_clips",
    )

    scene: Mapped["Scene"] = relationship(
        "Scene",
        back_populates="voice_clips",
    )