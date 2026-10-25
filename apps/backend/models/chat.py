from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, text
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base
from apps.backend.models.admin import _uuid_pk


class Conversation(Base):
    """Account-owned conversation; a null account identifies a guest conversation."""

    __tablename__ = "conversation"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # AdminAccount is the compatibility class for the current integer-keyed account table.
    account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("account.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    heritage_id: Mapped[int | None] = mapped_column(
        ForeignKey("heritage.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", passive_deletes=True,
        order_by="(ChatMessage.created_at, ChatMessage.id)",
    )

    __table_args__ = (Index("idx_conversation_account_updated", "account_id", "updated_at", "id"),)


class ChatSession(Base):
    __tablename__ = "chat_session"

    id: Mapped[uuid.UUID] = _uuid_pk()
    ip_hash: Mapped[str] = mapped_column(Text, nullable=False, comment="hash để anonymize")
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_session_ip", "ip_hash", created_at.desc()),)


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chat_session.id", ondelete="CASCADE"), nullable=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversation.id", ondelete="CASCADE"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False, server_default=text("'[]'")
    )
    abstained: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", comment="từ chối trả lời ngoài phạm vi")
    retrieval_strategy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    corpus_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    conversation: Mapped["Conversation | None"] = relationship(back_populates="messages")
    citation_records: Mapped[list["MessageCitation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan", passive_deletes=True,
        order_by="MessageCitation.id",
    )

    __table_args__ = (
        Index("idx_msg_session", "session_id", created_at),
        Index("idx_msg_conversation_created", "conversation_id", "created_at", "id"),
        CheckConstraint(
            "(session_id IS NOT NULL AND conversation_id IS NULL) OR "
            "(session_id IS NULL AND conversation_id IS NOT NULL)",
            name="chk_msg_one_parent",
        ),
        CheckConstraint("role IN ('user','assistant')", name="chk_msg_role"),
        CheckConstraint(
            "role = 'user' OR abstained OR jsonb_array_length(citations) > 0",
            name="chk_msg_citations",
        ),
    )


class MessageCitation(Base):
    __tablename__ = "message_citation"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chat_message.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    message: Mapped["ChatMessage"] = relationship(back_populates="citation_records")


class ChatFeedback(Base):
    __tablename__ = "chat_feedback"

    id: Mapped[uuid.UUID] = _uuid_pk()
    message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chat_message.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="(-1, 1)")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("rating IN (-1, 1)", name="chk_feedback_rating"),
    )
