from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, Numeric,
    REAL, String, Text, Table, UniqueConstraint, text,
)
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.types import Vec3
from backend.db.base import Base
from backend.models.admin import _uuid_pk


class Tour(Base):
    __tablename__ = "tour"

    id: Mapped[uuid.UUID] = _uuid_pk()
    site_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("site.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, server_default="vi")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    tagline: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    splash_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ambient_audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_sky: Mapped[str] = mapped_column(String(32), nullable=False, server_default="midday")
    default_camera_clip_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment="flythrough mở đầu")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1", comment="ETag + chống ghi đè")
    published_at: Mapped[datetime | None] = mapped_column(nullable=True, comment="NULL = draft, API ẩn")
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("admin_account.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("slug", "locale", name="uq_tour_slug_locale"),
        Index("idx_tour_site", "site_id"),
        Index("idx_tour_pub", "slug", "locale", postgresql_where=text("published_at IS NOT NULL")),
    )


class Story(Base):
    __tablename__ = "story"

    id: Mapped[uuid.UUID] = _uuid_pk()
    tour_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tour.id", ondelete="CASCADE"), nullable=False
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("scene.id", ondelete="SET NULL"), nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="HTML")

    camera_clip_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_name: Mapped[str | None] = mapped_column(Text, nullable=True, comment="chọn camera trong file nhiều camera")
    clip_start_s: Mapped[float | None] = mapped_column(Numeric(8, 3), nullable=True)
    clip_end_s: Mapped[float | None] = mapped_column(Numeric(8, 3), nullable=True)
    start_camera_position: Mapped[list[float] | None] = mapped_column(Vec3, nullable=True)
    start_camera_target: Mapped[list[float] | None] = mapped_column(Vec3, nullable=True)
    zoom_camera_position: Mapped[list[float] | None] = mapped_column(Vec3, nullable=True)
    zoom_camera_target: Mapped[list[float] | None] = mapped_column(Vec3, nullable=True)

    camera_fov: Mapped[float | None] = mapped_column(
        REAL, nullable=True, comment="CHECK 10..120"
    )
    pan_enable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    instant_move: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sky: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="NULL = kế thừa tour.default_sky")
    free_explore: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    explore_area: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_story_tour", "tour_id", "order_index"),
        Index("idx_story_scene", "scene_id"),
        UniqueConstraint("tour_id", "order_index", name="uq_story_order"),
        CheckConstraint(
            "clip_start_s IS NULL OR clip_end_s IS NULL OR clip_end_s > clip_start_s",
            name="chk_story_clip_range",
        ),
        CheckConstraint(
            "camera_clip_url IS NOT NULL OR start_camera_position IS NOT NULL",
            name="chk_story_has_camera",
        ),
        CheckConstraint(
            "start_camera_position IS NULL OR start_camera_target IS NULL OR start_camera_position <> start_camera_target",
            name="chk_story_pos_ne_target",
        ),
        CheckConstraint(
            "(zoom_camera_position IS NULL) = (zoom_camera_target IS NULL)",
            name="chk_story_zoom_pair",
        ),
        CheckConstraint(
            "NOT free_explore OR explore_area IS NOT NULL",
            name="chk_story_explore",
        ),
    )


class Narration(Base):
    __tablename__ = "narration"

    id: Mapped[uuid.UUID] = _uuid_pk()
    story_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("story.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    audio_url: Mapped[str] = mapped_column(Text, nullable=False)
    captions_vtt_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, comment="FE dùng để tính drift")
    voice_credit: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("duration_ms > 0", name="chk_narration_duration"),
    )


class Transcript(Base):
    __tablename__ = "transcript"

    id: Mapped[uuid.UUID] = _uuid_pk()
    story_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("story.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_transcript_story", "story_id", "seq"),
        CheckConstraint("end_ms > start_ms", name="chk_transcript_span"),
        UniqueConstraint("story_id", "seq", name="uq_transcript_seq"),
    )


class Highlight(Base):
    __tablename__ = "highlight"

    id: Mapped[uuid.UUID] = _uuid_pk()
    story_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("story.id", ondelete="CASCADE"), nullable=False
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("scene.id", ondelete="SET NULL"), nullable=True
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id", ondelete="SET NULL"), nullable=True,
        comment="NULLABLE: không phải highlight nào cũng là entity trong KG",
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    orb_position: Mapped[list[float]] = mapped_column(Vec3, nullable=False, comment="vị trí quả cầu")
    camera_position: Mapped[list[float]] = mapped_column(Vec3, nullable=False, comment="pose khi bấm vào")
    camera_target: Mapped[list[float]] = mapped_column(Vec3, nullable=False)

    popup_title: Mapped[str] = mapped_column(Text, nullable=False)
    popup_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    media_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_hl_story", "story_id", "order_index"),
        Index("idx_hl_entity", "entity_id"),
        CheckConstraint(
            "media_type IS NULL OR media_type IN ('image','video','audio','model')",
            name="chk_hl_media_type",
        ),
        CheckConstraint(
            "(media_url IS NULL) = (media_type IS NULL)",
            name="chk_hl_media_pair",
        ),
        CheckConstraint(
            "camera_position <> camera_target",
            name="chk_hl_cam_ne_tgt",
        ),
    )


class Citation(Base):
    __tablename__ = "citation"

    id: Mapped[uuid.UUID] = _uuid_pk()
    passage_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passage.id", ondelete="CASCADE"), nullable=True
    )
    transcript_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("transcript.id", ondelete="CASCADE"), nullable=True
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_citation_passage", "passage_id"),
        Index("idx_citation_transcript", "transcript_id"),
        CheckConstraint(
            "(passage_id IS NOT NULL)::int + (transcript_id IS NOT NULL)::int = 1",
            name="chk_citation_one_source",
        ),
    )


class TourStop(Base):
    """Mapping of v_tour_stop VIEW (schema.sql:515). Read-only — do not INSERT/UPDATE.

    Single query trả về cả tour + các stops (tránh N+1).
    Phụ thuộc vào 5 bảng JOIN: tour, story, scene, narration + subquery highlight.
    """
    __table__ = Table(
        "v_tour_stop",
        Base.metadata,
        Column("tour_id", PG_UUID(as_uuid=True), primary_key=True),
        Column("slug", Text),
        Column("locale", String(8)),
        Column("tour_title", Text),
        Column("tagline", Text),
        Column("location_label", Text),
        Column("splash_image_url", Text),
        Column("ambient_audio_url", Text),
        Column("default_camera_clip_url", Text),
        Column("revision", Integer),
        Column("published_at", DateTime(timezone=True), nullable=True),
        Column("story_id", PG_UUID(as_uuid=True), primary_key=True),
        Column("order_index", Integer),
        Column("scene_title", Text),
        Column("scene_description", Text),
        Column("camera_clip_url", Text),
        Column("camera_name", Text),
        Column("clip_start_s", Numeric(8, 3)),
        Column("clip_end_s", Numeric(8, 3)),
        Column("start_camera_position", Vec3()),
        Column("start_camera_target", Vec3()),
        Column("zoom_camera_position", Vec3()),
        Column("zoom_camera_target", Vec3()),
        Column("camera_fov", REAL),
        Column("pan_enable", Boolean),
        Column("instant_move", Boolean),
        Column("sky", String(32)),
        Column("free_explore", Boolean),
        Column("explore_area", JSONB),
        Column("bbox_min", Vec3()),
        Column("bbox_max", Vec3()),
        Column("transform_7dof", JSONB),
        Column("model_url", Text),
        Column("narration_url", Text),
        Column("captions_vtt_url", Text),
        Column("narration_duration_ms", Integer),
        Column("highlights", JSONB),
    )
    __mapper_args__ = {"primary_key": [__table__.c.tour_id, __table__.c.story_id]}
