from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Float, ForeignKey, Index, Integer,
    String, Text,
)
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.db.base import Base
from apps.backend.models.admin import _uuid_pk


class Site(Base):
    """site — legacy site-based 3D node. Kept as UUID (legacy migrations).

    Schema.sql targets heritage/scene; `site` remains for the legacy tour
    slice (tour.py, chat.py) and is out of the BIGINT heritage remap.
    """

    __tablename__ = "site"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document.id", ondelete="SET NULL"), nullable=True
    )
    source_passage_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passage.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("idx_site_entity", "entity_id"),)


class RawAsset(Base):
    """raw_asset — legacy capture metadata for photogrammetry/splat sources."""

    __tablename__ = "raw_asset"

    id: Mapped[uuid.UUID] = _uuid_pk()
    scene_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("scene.id", ondelete="CASCADE"), nullable=False
    )
    capture_method: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_location: Mapped[str] = mapped_column(Text, nullable=False, comment="path local/SSD ngoài, không public")
    image_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_raw_scene", "scene_id"),
        CheckConstraint(
            "capture_method IN ('photogrammetry','gaussian_splat_source','drone_video','lidar')",
            name="chk_capture_method",
        ),
    )