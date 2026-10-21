from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base


class SkyPreset(Base):
    __tablename__ = "sky_preset"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )

    turbidity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    rayleigh: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    elevation: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    azimuth: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    exposure: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    light_settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scenes: Mapped[list["Scene"]] = relationship(
        "Scene",
        back_populates="sky_preset",
    )