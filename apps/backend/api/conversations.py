"""HTTP adapters for account-owned conversations around a supplied AI pipeline."""
from __future__ import annotations

import logging
import asyncio
from contextlib import contextmanager
from uuid import UUID
from types import SimpleNamespace

from fastapi import Depends, HTTPException, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.backend.core.security import get_current_user
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.schemas.chat import (
    ChatAnswer, ChatMessageCreate, ChatResponse, ConversationDetailResponse, ConversationResponse,
)
from apps.backend.services.conversations import ChatServiceError, ConversationService
from apps.backend.services import chat_fallback
from apps.backend.services.tour_guide import resolve_tour_context

log = logging.getLogger(__name__)
optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_account_id(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer)):
    if credentials is None:
        if request.headers.get("authorization") is not None:
            raise HTTPException(401, "Thông tin xác thực không hợp lệ.")
        return None
    claims = await get_current_user(credentials)
    try:
        account_id = int(claims["sub"])
        if account_id <= 0 or claims.get("type") not in (None, "access"):
            raise ValueError()
        return account_id
    except (KeyError, ValueError, TypeError):
        raise HTTPException(401, "Token tài khoản không hợp lệ.") from None


async def get_authenticated_account_id(account_id: int | None = Depends(get_optional_account_id)):
    if account_id is None:
        raise HTTPException(401, "Bạn cần đăng nhập để quản lý cuộc trò chuyện.")
    return account_id


async def get_chat_db():
    if AsyncSessionLocal.kw.get("bind") is None:
        raise HTTPException(503, "Cơ sở dữ liệu hội thoại chưa được cấu hình.")
    async with AsyncSessionLocal() as db:
        yield db


def get_conversation_service(db=Depends(get_chat_db)):
    return ConversationService(db)


async def validated_tour_context(request):
    """Both chat adapters validate optional scene identity before retrieval."""
    if request.tour_context is None:
        return None
    if AsyncSessionLocal.kw.get("bind") is None:
        raise HTTPException(503, "Không thể xác minh ngữ cảnh tham quan lúc này.")
    async with AsyncSessionLocal() as db:
        try:
            return await resolve_tour_context(request, db)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None


@contextmanager
def conversation_errors():
    try:
        yield
    except ChatServiceError as error:
        codes = {"unauthorized": 401, "forbidden": 403, "not_found": 404, "bad_request": 400, "timeout": 504}
        raise HTTPException(codes.get(error.code, 500), error.detail) from None
    except HTTPException:
        raise
    except Exception as error:
        log.error("Conversation transaction failed (%s)", type(error).__name__)
        raise HTTPException(500, "Không thể lưu hoặc đọc cuộc trò chuyện. Vui lòng thử lại.") from None


def mount_conversation_routes(router, get_repository, pipeline):
    """Use identical persistence/auth semantics for both existing router paths."""
    @router.post("/chat/message", response_model=ChatResponse, status_code=201, responses={
        401: {"description": "JWT không hợp lệ"}, 403: {"description": "Không phải chủ sở hữu"},
        500: {"description": "AI hoặc lưu trữ hội thoại lỗi"}, 504: {"description": "AI quá 30 giây"},
    })
    async def create_chat_message(
        request: ChatMessageCreate,
        account_id: int | None = Depends(get_optional_account_id),
        service: ConversationService = Depends(get_conversation_service),
        repository=Depends(get_repository),
    ):
        async def answerer(message, history):
            local_fallback = chat_fallback.development_fallback_enabled()
            retrieved = None
            async def search_evidence(*args, **kwargs):
                nonlocal retrieved
                retrieved = await repository.search_evidence(*args, **kwargs)
                return retrieved
            async def fallback():
                if message.active_area_id:
                    answer = chat_fallback.scoped_service_unavailable(message.active_area_id)
                    if message.tour_context:
                        snapshot = await validated_tour_context(message)
                        answer = answer.model_copy(update={
                            "reply_context": snapshot.model_copy(update={"story_id": None}),
                            "follow_up_questions": [],
                        })
                    return answer
                evidence = retrieved.evidence if retrieved is not None else []
                return await chat_fallback.development_answer(
                    message.message, history=[item.model_dump() for item in history],
                    context="\n\n".join(item.text for item in evidence)[:4800],
                    sources=[item.to_source() for item in evidence],
                )
            try:
                inference = pipeline(message.model_copy(update={
                    "conversation_context": history,
                }), SimpleNamespace(search_evidence=search_evidence))
                result = await asyncio.wait_for(inference, timeout=chat_fallback.LOCAL_INFERENCE_TIMEOUT_SECONDS) if local_fallback else await inference
                return ChatAnswer.model_validate(result)
            except TimeoutError:
                if local_fallback:
                    return await fallback()
                raise ChatServiceError("timeout", "AI phản hồi quá thời gian chờ 30 giây.") from None
            except HTTPException as error:
                if error.status_code == 422:
                    raise
                if local_fallback and error.status_code in {500, 503, 504}:
                    return await fallback()
                if error.status_code == 504:
                    raise ChatServiceError("timeout", "AI phản hồi quá thời gian chờ 30 giây.") from None
                raise ChatServiceError("inference", "Hệ thống AI hiện không thể trả lời. Vui lòng thử lại.") from None
        with conversation_errors():
            return await service.send(request, account_id, answerer)

    @router.get("/chat/conversations", response_model=list[ConversationResponse])
    async def list_conversations(
        account_id: int = Depends(get_authenticated_account_id),
        service: ConversationService = Depends(get_conversation_service),
        limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
    ):
        with conversation_errors():
            return await service.list_conversations(account_id, limit=limit, offset=offset)

    @router.get("/chat/conversations/{conversation_id}/messages", response_model=ConversationDetailResponse)
    async def get_messages(
        conversation_id: UUID,
        account_id: int = Depends(get_authenticated_account_id),
        service: ConversationService = Depends(get_conversation_service),
        limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
    ):
        with conversation_errors():
            return await service.get_detail(conversation_id, account_id, limit=limit, offset=offset)

    @router.delete("/chat/conversations/{conversation_id}", status_code=204, response_class=Response)
    async def delete_conversation(
        conversation_id: UUID,
        account_id: int = Depends(get_authenticated_account_id),
        service: ConversationService = Depends(get_conversation_service),
    ):
        with conversation_errors():
            await service.delete_conversation(conversation_id, account_id)
        return Response(status_code=204)
