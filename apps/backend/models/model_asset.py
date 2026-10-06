from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base


class ModelAsset(Base):
    __tablename__ = "model_asset"

    id: Mapped[int] = mapped_column(primary_key=True)

    scene_id: Mapped[int] = mapped_column(
        ForeignKey("scene.id", ondelete="CASCADE"),
        nullable=False,
    )

    file_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    format: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="glb",
    )

    lod_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    compression: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scene: Mapped["Scene"] = relationship(
        "Scene",
        back_populates="model_assets",
    )