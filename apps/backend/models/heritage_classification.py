"""Editorial catalog projection, classifications and durable SQL-change queue."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Identity, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.db.base import Base


class HeritageCategory(Base):
    __tablename__ = "heritage_categories"
    key: Mapped[str] = mapped_column(String(48), primary_key=True)
    name_vi: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    parent_key: Mapped[str | None] = mapped_column(ForeignKey("heritage_categories.key"))


class CulturalContent(Base):
    __tablename__ = "heritage_content"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source_heritage_id: Mapped[int | None] = mapped_column(ForeignKey("heritage.id", ondelete="CASCADE"), unique=True)
    slug: Mapped[str] = mapped_column(String(250), unique=True)
    title: Mapped[str] = mapped_column(Text)
    tagline: Mapped[str | None] = mapped_column(Text)
    headline: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    card_image_url: Mapped[str | None] = mapped_column(Text)
    splash_image_url: Mapped[str | None] = mapped_column(Text)
    publish_state: Mapped[str] = mapped_column(String(32), server_default="draft")
    entity_type_hint: Mapped[str | None] = mapped_column(String(16))
    entity_type: Mapped[str | None] = mapped_column(String(16))
    source_url: Mapped[str | None] = mapped_column(Text)
    verified_metadata: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    knowledge_entity_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("entity.id", ondelete="SET NULL"))
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_document.id", ondelete="SET NULL"))
    interactive_highlight_id: Mapped[int | None] = mapped_column(ForeignKey("interactive_highlight.id", ondelete="SET NULL"))
    input_revision: Mapped[int] = mapped_column(Integer, server_default="1")
    classified_revision: Mapped[int] = mapped_column(Integer, server_default="0")
    classification_status: Mapped[str] = mapped_column(String(16), server_default="pending")
    locked_by_admin: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_featured: Mapped[bool] = mapped_column(Boolean, server_default="false")
    featured_rank: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HeritageClassification(Base):
    __tablename__ = "heritage_classifications"
    content_id: Mapped[int] = mapped_column(ForeignKey("heritage_content.id", ondelete="CASCADE"), primary_key=True)
    category_key: Mapped[str] = mapped_column(ForeignKey("heritage_categories.key"), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean)
    confidence: Mapped[float] = mapped_column(Float)
    classification_source: Mapped[str] = mapped_column(String(16))
    reasoning_summary: Mapped[str] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentRelation(Base):
    __tablename__ = "heritage_content_relations"
    subject_id: Mapped[int] = mapped_column(ForeignKey("heritage_content.id", ondelete="CASCADE"), primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("heritage_content.id", ondelete="CASCADE"), primary_key=True)
    relation_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_url: Mapped[str] = mapped_column(Text)


class ClassificationJob(Base):
    __tablename__ = "heritage_classification_jobs"
    content_id: Mapped[int] = mapped_column(ForeignKey("heritage_content.id", ondelete="CASCADE"), primary_key=True)
    generation: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), server_default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    last_error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClassificationAudit(Base):
    __tablename__ = "heritage_classification_audit"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("heritage_content.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    input_revision: Mapped[int] = mapped_column(Integer)
    actor: Mapped[str] = mapped_column(String(100))
    before: Mapped[dict] = mapped_column(JSONB)
    after: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
