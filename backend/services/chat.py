"""Service layer cho Chatbot — quản lý session + message persistence.

Schema.sql: chat_session, chat_message, chat_feedback.
Service này giữ session state trong DB thay vì in-memory, hỗ trợ multi-instance.
"""
from __future__ import annotations

import uuid

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import ChatFeedback, ChatMessage, ChatSession


class ChatSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(
        self, ip_hash: str, site_id: uuid.UUID | None = None,
        user_agent: str | None = None,
    ) -> ChatSession:
        """Tìm session theo ip_hash (session per IP), tạo nếu chưa có.

        Schema.sql thiết kế 1 session ~ 1 IP. Không có session_token vì đây là
        public chat, dùng ip_hash để gom các tin nhắn trong phiên.
        """
        existing = await self.db.execute(
            select(ChatSession).where(
                ChatSession.ip_hash == ip_hash,
            ).order_by(ChatSession.created_at.desc()).limit(1)
        )
        row = existing.scalar_one_or_none()
        if row:
            return row

        result = await self.db.execute(
            insert(ChatSession)
            .values(
                ip_hash=ip_hash,
                site_id=site_id,
                user_agent=user_agent,
            )
            .returning(ChatSession)
        )
        await self.db.commit()
        return result.scalar_one()

    async def get_history(
        self, session_id: uuid.UUID,
    ) -> list[ChatMessage]:
        """Lịch sử tin nhắn của session để dùng làm context LLM."""
        rows = await self.db.execute(
            select(ChatMessage).where(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at.asc())
        )
        return list(rows.scalars().all())

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        citations: list[dict] | None = None,
        abstained: bool = False,
        retrieval_strategy: str | None = None,
        latency_ms: int | None = None,
        model: str | None = None,
        corpus_version: int | None = None,
    ) -> ChatMessage:
        """Persist một tin nhắn (user hoặc assistant) vào session."""
        result = await self.db.execute(
            insert(ChatMessage)
            .values(
                session_id=session_id,
                role=role,
                content=content,
                citations=citations or [],
                abstained=abstained,
                retrieval_strategy=retrieval_strategy,
                latency_ms=latency_ms,
                model=model,
                corpus_version=corpus_version,
            )
            .returning(ChatMessage)
        )
        await self.db.commit()
        return result.scalar_one()

    async def add_feedback(
        self, message_id: uuid.UUID, rating: int, comment: str | None = None,
    ) -> ChatFeedback:
        """Ghi feedback cho một assistant message."""
        result = await self.db.execute(
            insert(ChatFeedback)
            .values(message_id=message_id, rating=rating, comment=comment)
            .returning(ChatFeedback)
        )
        await self.db.commit()
        return result.scalar_one()
