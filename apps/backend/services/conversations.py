"""Transactional conversation persistence around the existing grounded-answer pipeline."""
from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.models.admin import AdminAccount
from apps.backend.models.chat import ChatMessage, Conversation, MessageCitation
from apps.backend.models.heritage import Heritage
from apps.backend.schemas.chat import (
    ChatAnswer as GroundedAnswer, ChatContextMessage, ChatMessageCreate, ChatMessageResponse, ChatOutcome,
    ChatResponse, ConversationDetailResponse, MAX_CONTEXT_MESSAGES,
    ConversationResponse, MessageCitationResponse,
)
from apps.backend.services.chat_context import bounded_history

CHAT_TIMEOUT_SECONDS = 30


class ChatServiceError(Exception):
    """Application error translated into HTTP only at the router boundary."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def citation_from_source(source: dict, message_id: UUID) -> MessageCitation:
    url = source.get("url") or None
    if url:
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                url = None
        except (TypeError, ValueError):
            url = None
    score = source.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score):
        score = None
    return MessageCitation(
        id=uuid4(), message_id=message_id,
        source_title=str(source.get("doc") or f"Passage {source.get('passage_id', '')}").strip(),
        source_url=url, relevance_score=score,
    )


def message_response(message: ChatMessage) -> ChatMessageResponse:
    outcome = ChatOutcome.model_validate({
        **(message.response_metadata or {}), "abstained": message.abstained,
    })
    return ChatMessageResponse(
        **outcome.outcome_data(), id=message.id, conversation_id=message.conversation_id,
        role=message.role, content=message.content, created_at=message.created_at,
        citations=message.citation_records,
    )


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def require_account(self, account_id: int) -> None:
        account = (await self.db.execute(
            select(AdminAccount.id, AdminAccount.is_active).where(AdminAccount.id == account_id)
        )).first()
        if account is None or not account.is_active:
            raise ChatServiceError("unauthorized", "Tài khoản không tồn tại hoặc đã bị khóa.")

    async def require_owned(self, conversation_id: UUID, account_id: int | None, *, lock: bool = False) -> Conversation:
        if account_id is None:
            raise ChatServiceError("forbidden", "Bạn cần đăng nhập để truy cập cuộc trò chuyện đã lưu.")
        query = select(Conversation).where(Conversation.id == conversation_id)
        if lock:
            query = query.with_for_update()
        conversation = (await self.db.execute(query)).scalar_one_or_none()
        if conversation is None:
            raise ChatServiceError("not_found", "Không tìm thấy cuộc trò chuyện.")
        if conversation.account_id != account_id:
            raise ChatServiceError("forbidden", "Bạn không có quyền truy cập cuộc trò chuyện này.")
        return conversation

    async def list_conversations(self, account_id: int, *, limit: int = 50, offset: int = 0) -> list[ConversationResponse]:
        await self.require_account(account_id)
        rows = await self.db.execute(
            select(Conversation).where(Conversation.account_id == account_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc()).limit(limit).offset(offset)
        )
        return [ConversationResponse.model_validate(row) for row in rows.scalars().all()]

    async def get_detail(
        self, conversation_id: UUID, account_id: int, *, limit: int = 100, offset: int = 0,
    ) -> ConversationDetailResponse:
        await self.require_account(account_id)
        conversation = await self.require_owned(conversation_id, account_id)
        rows = await self.db.execute(
            select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
            .options(selectinload(ChatMessage.citation_records))
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc()).limit(limit).offset(offset)
        )
        return ConversationDetailResponse(
            **ConversationResponse.model_validate(conversation).model_dump(),
            messages=[message_response(row) for row in rows.scalars().all()],
        )

    async def delete_conversation(self, conversation_id: UUID, account_id: int) -> None:
        try:
            await self.require_account(account_id)
            conversation = await self.require_owned(conversation_id, account_id, lock=True)
            await self.db.delete(conversation)
            await self.db.commit()
        except BaseException:
            await self.db.rollback()
            raise

    async def send(
        self, request: ChatMessageCreate, account_id: int | None,
        answerer: Callable[[ChatMessageCreate, list[ChatContextMessage]], Awaitable[GroundedAnswer]],
    ) -> ChatResponse:
        try:
            if account_id is not None:
                await self.require_account(account_id)
            if request.conversation_id is not None:
                conversation = await self.require_owned(request.conversation_id, account_id, lock=True)
                if request.heritage_id is not None and request.heritage_id != conversation.heritage_id:
                    raise ChatServiceError("bad_request", "Di sản không khớp với cuộc trò chuyện hiện tại.")
                if request.conversation_context:
                    raise ChatServiceError("bad_request", "Hội thoại đã lưu sử dụng lịch sử từ máy chủ; không nhận lịch sử thay thế.")
                rows = (await self.db.execute(
                    select(ChatMessage.role, ChatMessage.content)
                    .where(ChatMessage.conversation_id == conversation.id)
                    .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(MAX_CONTEXT_MESSAGES)
                )).all()
                history = bounded_history(rows)
            else:
                conversation = Conversation(
                    id=uuid4(), account_id=account_id, title=request.message[:200], heritage_id=request.heritage_id,
                )
                history = request.conversation_context

            effective_request = request
            if conversation.heritage_id is not None:
                heritage = (await self.db.execute(
                    select(Heritage.id, Heritage.title, Heritage.region).where(
                        Heritage.id == conversation.heritage_id, Heritage.publish_state == "published",
                    )
                )).first()
                if heritage is None:
                    raise ChatServiceError("not_found", "Không tìm thấy di sản đã công bố.")
                if not request.heritage_context:
                    effective_request = request.model_copy(update={
                        "heritage_context": {"title": heritage.title, "region": heritage.region},
                    })

            if request.conversation_id is None:
                self.db.add(conversation)

            answer = await asyncio.wait_for(answerer(effective_request, history), timeout=CHAT_TIMEOUT_SECONDS)
            if not answer.answer.strip() or answer.resolution_status == "unavailable":
                raise ChatServiceError("inference", "Hệ thống AI hiện không thể trả lời. Vui lòng thử lại.")
            if answer.answer_type == "answered" and not answer.sources:
                raise ChatServiceError("inference", "Câu trả lời chưa có bằng chứng hợp lệ. Vui lòng thử lại.")

            now = datetime.now(timezone.utc)
            user_message = ChatMessage(
                id=uuid4(), conversation_id=conversation.id, role="user", content=request.message,
                citations=[], abstained=False, created_at=now, citation_records=[],
            )
            assistant_message = ChatMessage(
                id=uuid4(), conversation_id=conversation.id, role="assistant", content=answer.answer,
                citations=answer.sources, abstained=answer.abstained, response_metadata=answer.outcome_data(),
                retrieval_strategy="development_mock" if answer.answer_type == "development_mock" else "opensearch_hybrid",
                created_at=now + timedelta(microseconds=1),
            )
            assistant_message.citation_records = [citation_from_source(source, assistant_message.id) for source in answer.sources]
            conversation.updated_at = assistant_message.created_at
            self.db.add_all([user_message, assistant_message])
            await self.db.flush()
            response = ChatResponse(
                conversation_id=conversation.id, message_id=assistant_message.id, answer=answer.answer,
                citations=[MessageCitationResponse.model_validate(citation) for citation in assistant_message.citation_records],
                **answer.outcome_data(),
            )
            # Both turns and every citation commit as one unit before the response is sent.
            await self.db.commit()
            return response
        except TimeoutError:
            await self.db.rollback()
            raise ChatServiceError("timeout", "AI xử lý quá thời gian 30 giây. Vui lòng thử lại.") from None
        except BaseException:
            await self.db.rollback()
            raise
