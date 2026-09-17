from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, text,
)
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.types import Vec3, JsonB
from backend.db.base import Base
from backend.models.admin import _uuid_pk


class Site(Base):
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


class Scene(Base):
    __tablename__ = "scene"

    id: Mapped[uuid.UUID] = _uuid_pk()
    site_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("site.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    transform_7dof: Mapped[dict] = mapped_column(
        JsonB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="JSONB {translate:[x,y,z],rotate:[x,y,z,w],scale:n}",
    )
    bbox_min: Mapped[list[float] | None] = mapped_column(Vec3, nullable=True)
    bbox_max: Mapped[list[float] | None] = mapped_column(Vec3, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_scene_site", "site_id", "order_index"),
        CheckConstraint(
            "(transform_7dof ? 'translate') AND (transform_7dof ? 'rotate') AND (transform_7dof ? 'scale')",
            name="chk_scene_7dof",
        ),
    )


class ModelAsset(Base):
    __tablename__ = "model_asset"

    id: Mapped[uuid.UUID] = _uuid_pk()
    scene_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("scene.id", ondelete="CASCADE"), nullable=False
    )
    lod_level: Mapped[int] = mapped_column(Integer, nullable=False, comment="0 = cao nhất")
    file_url: Mapped[str] = mapped_column(Text, nullable=False, comment="URL CDN, KHÔNG lưu blob")
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True, comment="cache-busting tên file")
    format: Mapped[str] = mapped_column(String(16), nullable=False, server_default="glb")
    compression: Mapped[str | None] = mapped_column(String(32), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(
        name="file_size_bytes", nullable=True
    )
    triangle_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    gpu_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_proxy: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", comment="bản nhẹ raycast/preview")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_asset_scene", "scene_id", "lod_level"),
        CheckConstraint(
            "format IN ('glb','gltf','splat','sog','ply')",
            name="chk_asset_format",
        ),
        CheckConstraint("file_size_bytes > 0", name="chk_asset_size"),
        UniqueConstraint("scene_id", "lod_level", name="uq_asset_scene_lod"),
    )


class RawAsset(Base):
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
