"""Persisted admin settings and durable reindex queue; no simulated job state."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.db.base import Base

json_type = JSON().with_variant(JSONB(), "postgresql")


def now():
    return datetime.now(timezone.utc)


class RagPipeline(Base):
    __tablename__ = "rag_pipeline"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    chunking: Mapped[dict] = mapped_column(json_type)
    embedding: Mapped[dict] = mapped_column(json_type)
    retrieval: Mapped[dict] = mapped_column(json_type)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ReindexJob(Base):
    __tablename__ = "rag_reindex_job"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','RUNNING','COMPLETED','FAILED')"),
        CheckConstraint("(status IN ('PENDING','RUNNING') AND active_slot = 1) OR "
                        "(status IN ('COMPLETED','FAILED') AND active_slot IS NULL)"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pipeline_id: Mapped[str] = mapped_column(ForeignKey("rag_pipeline.id", ondelete="RESTRICT"), index=True)
    pipeline_revision: Mapped[int] = mapped_column(Integer)
    config_snapshot: Mapped[dict] = mapped_column(json_type)
    document_ids: Mapped[list] = mapped_column(json_type)
    document_revisions: Mapped[dict] = mapped_column(json_type)
    requested_by: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    # A single active writer across pipelines prevents overlapping source rewrites.
    active_slot: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    processed_documents: Mapped[int] = mapped_column(Integer, default=0)
    indexed_passages: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
