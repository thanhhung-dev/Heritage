"""Durable upload ownership and destination reservations, separate from RAG."""
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.db.base import Base


class LibraryUpload(Base):
    __tablename__ = "knowledge_library_upload"
    __table_args__ = (
        CheckConstraint("bucket = 'knowledge-heritage'", name="ck_library_bucket"),
        CheckConstraint("size_bytes > 0 AND size_bytes <= 33554432", name="ck_library_size"),
        CheckConstraint("status IN ('PENDING','COMPLETED','EXPIRED','CONFLICT')", name="ck_library_status"),
        CheckConstraint("(status = 'PENDING' AND reservation_key = final_key) OR "
                        "(status <> 'PENDING' AND reservation_key IS NULL)", name="ck_library_reservation"),
        CheckConstraint("status <> 'PENDING' OR reservation_key IS NOT NULL", name="ck_library_pending"),
        Index("ix_library_expiry", "status", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[int] = mapped_column(BigInteger, index=True)
    bucket: Mapped[str] = mapped_column(String(32))
    final_key: Mapped[str] = mapped_column(Text)
    reservation_key: Mapped[str | None] = mapped_column(Text, unique=True)
    staging_key: Mapped[str] = mapped_column(Text, unique=True)
    filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    final_etag: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
