from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Computed, ForeignKey, Index, Integer, Numeric,
    REAL, String, Text, UniqueConstraint, text,
)
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION, UUID as PG_UUID, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.models.admin import _uuid_pk


class Document(Base):
    __tablename__ = "document"

    id: Mapped[uuid.UUID] = _uuid_pk()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False, comment="domain region_code CHECK IN ('hue','da_nang')")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, comment="toàn văn gốc, để re-chunk")
    license: Mapped[str | None] = mapped_column(Text, nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(name="withdrawn_at", nullable=True, comment="rút nguồn, không xoá cứng")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_document_region", "region"),
        CheckConstraint(
            "withdrawn_at IS NULL",
            name="_doc_not_withdrawn",
        ),
    )




class Passage(Base):
    __tablename__ = "passage"

    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    corpus_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', text)", persisted=True),
        nullable=True,
        comment="generated, do not write",
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_passage_document", "document_id", "corpus_version"),
        Index("idx_passage_tsv", "tsv"),
        CheckConstraint("char_start >= 0", name="chk_passage_char_start"),
        CheckConstraint("char_end > char_start", name="chk_passage_span"),
        UniqueConstraint("document_id", "corpus_version", "char_start", name="uq_passage_span"),
    )


class Entity(Base):
    __tablename__ = "entity"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(
        ARRAY(DOUBLE_PRECISION), nullable=True,
        comment="FLOAT8[] - TODO: migrate to VECTOR(1024) after pgvector",
    )
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

    __table_args__ = (
        Index("idx_entity_name_trgm", "name"),
        Index("idx_entity_type", "type"),
        CheckConstraint(
            "type IN ('person','place','event','artifact')",
            name="chk_entity_type",
        ),
        UniqueConstraint("normalized_name", "type", name="uq_entity_norm"),
    )


class EntityAlias(Base):
    __tablename__ = "entity_alias"

    id: Mapped[uuid.UUID] = _uuid_pk()
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_alias: Mapped[str] = mapped_column(Text, nullable=False)
    alias_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="common")
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, server_default="1.0")
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document.id", ondelete="SET NULL"), nullable=True
    )
    source_passage_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passage.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_alias_entity", "entity_id"),
        Index("ix_entity_alias_normalized", "normalized_alias"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="chk_alias_conf"),
        CheckConstraint(
            "alias_type IN ('official','historical','common','typo')",
            name="chk_alias_type",
        ),
        UniqueConstraint("entity_id", "normalized_alias", name="uq_alias_entity_norm"),
    )


class Predicate(Base):
    __tablename__ = "predicate"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label_vi: Mapped[str] = mapped_column(Text, nullable=False)
    label_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_symmetric: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    inverse_of: Mapped[str | None] = mapped_column(
        Text, ForeignKey("predicate.code"), nullable=True
    )
    weight: Mapped[float] = mapped_column(REAL, nullable=False, server_default="1.0")


class Relation(Base):
    __tablename__ = "relation"

    id: Mapped[uuid.UUID] = _uuid_pk()
    subject_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), nullable=False
    )
    predicate: Mapped[str] = mapped_column(Text, nullable=False, comment="FK predicate.code")
    object_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, server_default="1.0")
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document.id", ondelete="SET NULL"), nullable=True
    )
    source_passage_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passage.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("subject_id", "predicate", "object_id", name="uq_relation"),
        Index("idx_relation_subj", "subject_id", "predicate"),
        Index("idx_relation_obj", "object_id", "predicate"),
        CheckConstraint("subject_id <> object_id", name="chk_relation_loop"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="chk_relation_conf"),
    )


class PlaceLocation(Base):
    """place_location — địa chỉ có nguồn và thời gian hiệu lực (migration guide §1.4).

    Không phải mỗi entity đều có location. Chỉ location status=verified mới dùng để trả lời khẳng định.
    valid_from/valid_to hỗ trợ địa chỉ lịch sử (đơn vị hành chính đổi tên, giải chấp...).
    """
    __tablename__ = "place_location"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE"), nullable=False
    )
    address: Mapped[str] = mapped_column(Text, nullable=False)
    ward: Mapped[str | None] = mapped_column(Text, nullable=True)
    district: Mapped[str | None] = mapped_column(Text, nullable=True)
    province: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(nullable=True)
    valid_to: Mapped[date | None] = mapped_column(nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="pending",
        comment="pending | verified | rejected | withdrawn",
    )
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_ploc_entity", "entity_id"),
        Index("ix_ploc_verified", "verification_status"),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="chk_ploc_valid_range",
        ),
        CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="chk_ploc_lat",
        ),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="chk_ploc_lng",
        ),
        CheckConstraint(
            "verification_status IN ('pending', 'verified', 'rejected', 'withdrawn')",
            name="chk_ploc_status",
        ),
    )
