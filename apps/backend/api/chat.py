"""Chat grounded in complete text chunks retrieved from OpenSearch."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.backend.core.llm import generate_response, get_generation_details
from apps.backend.core.observability import correlation_id, observe_grounded_qa, rag_observation
from apps.backend.core.search import PassageStore
from apps.backend.services.passages import PassageRepository
from apps.backend.core.security import get_current_user
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.schemas.chat import ChatMessageCreate, ChatResponse as PersistedChatResponse
from apps.backend.schemas.chat import ChatContextMessage, ConversationDetailResponse, ConversationResponse
from apps.backend.schemas.chat import LegacyChatRequest as ChatRequest, LegacyChatResponse as ChatResponse
from apps.backend.services.conversations import CHAT_TIMEOUT_SECONDS, ChatServiceError, ConversationService, GroundedAnswer
from apps.backend.services.chat_context import question_with_context, retrieval_question
from apps.backend.services import chat_fallback

log = logging.getLogger(__name__)
router = APIRouter()
optional_bearer = HTTPBearer(auto_error=False)


def account_id_from_claims(claims: dict) -> int:
    try:
        account_id = int(claims["sub"])
        if account_id <= 0 or claims.get("type") not in (None, "access"):
            raise ValueError
        return account_id
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token tài khoản không hợp lệ.") from None


async def get_optional_account_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
) -> int | None:
    if credentials is None:
        if request.headers.get("authorization") is not None:
            raise HTTPException(status_code=401, detail="Thông tin xác thực không hợp lệ.")
        return None
    return account_id_from_claims(await get_current_user(credentials))


async def get_chat_db():
    if AsyncSessionLocal.kw.get("bind") is None:
        raise HTTPException(status_code=503, detail="Cơ sở dữ liệu hội thoại chưa được cấu hình.")
    async with AsyncSessionLocal() as db:
        yield db


def get_conversation_service(db=Depends(get_chat_db)) -> ConversationService:
    return ConversationService(db)


def conversation_http_error(error: ChatServiceError) -> HTTPException:
    statuses = {"unauthorized": 401, "forbidden": 403, "not_found": 404, "bad_request": 400, "timeout": 504, "inference": 500}
    return HTTPException(status_code=statuses.get(error.code, 500), detail=error.detail)


@contextmanager
def conversation_errors():
    try:
        yield
    except ChatServiceError as error:
        raise conversation_http_error(error) from None
    except Exception:
        log.exception("Không thể xử lý cuộc trò chuyện")
        raise HTTPException(status_code=500, detail="Không thể xử lý cuộc trò chuyện. Vui lòng thử lại.") from None


def get_authenticated_account_id(current_user: dict = Depends(get_current_user)) -> int:
    return account_id_from_claims(current_user)


async def get_repository():
    async with PassageStore() as store:
        yield PassageRepository(store)


@router.post(
    "/chat/message", response_model=PersistedChatResponse, status_code=201,
    responses={401: {"description": "Token không hợp lệ"}, 403: {"description": "Không có quyền truy cập"},
               500: {"description": "AI hoặc cơ sở dữ liệu gặp lỗi"}, 504: {"description": "AI quá thời gian 30 giây"}},
)
async def create_chat_message(
    request: ChatMessageCreate,
    account_id: int | None = Depends(get_optional_account_id),
    service: ConversationService = Depends(get_conversation_service),
    repository: PassageRepository = Depends(get_repository),
):
    async def answerer(message_request: ChatMessageCreate, history: list[ChatContextMessage]) -> GroundedAnswer:
        # Reuse the existing retrieval, evidence gate, generation and observability.
        try:
            response = await _observed_chat(
                ChatRequest(
                    message=message_request.message, heritage_context=message_request.heritage_context,
                    scene_context=message_request.scene_context,
                    conversation_context=history,
                ), repository,
                development_fallback=chat_fallback.development_fallback_enabled(),
            )
        except HTTPException:
            raise ChatServiceError("inference", "Hệ thống AI hiện không thể trả lời. Vui lòng thử lại.") from None
        return response

    with conversation_errors():
        return await service.send(request, account_id, answerer)


@router.get("/chat/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    account_id: int = Depends(get_authenticated_account_id),
    service: ConversationService = Depends(get_conversation_service),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    with conversation_errors():
        return await service.list_conversations(account_id, limit=limit, offset=offset)


@router.get("/chat/conversations/{conversation_id}/messages", response_model=ConversationDetailResponse)
async def conversation_messages(
    conversation_id: UUID,
    account_id: int = Depends(get_authenticated_account_id),
    service: ConversationService = Depends(get_conversation_service),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
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


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, repository: PassageRepository = Depends(get_repository)):
    try:
        return await asyncio.wait_for(_observed_chat(req, repository), timeout=CHAT_TIMEOUT_SECONDS)
    except TimeoutError:
        raise HTTPException(504, "AI xử lý quá thời gian 30 giây. Vui lòng thử lại.") from None


async def _observed_chat(req: ChatRequest, repository: PassageRepository, *, development_fallback: bool = False):
    with rag_observation('rag.request', input={'question': req.message}, metadata={
        'correlation_id': correlation_id.get(), 'corpus_version': 'opensearch',
        'grounding_verified': False,
    }) as observation:
        response = await _chat(req, repository, development_fallback=development_fallback)
        observation.update(output=response.model_dump(), metadata={
            'resolution_status': response.resolution_status,
            'answer_type': response.answer_type,
            'selected_passage_ids': [s['passage_id'] for s in response.sources],
        })
        return response


async def _chat(req: ChatRequest, repository: PassageRepository, *, development_fallback: bool = False):
    started = time.perf_counter()
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message trống")
    question = question_with_context(req)
    search_question = retrieval_question(question, req.conversation_context)
    history = [message.model_dump() for message in req.conversation_context]

    # All answers require evidence, including requests from older use_rag clients.
    try:
        if development_fallback:
            result = await asyncio.wait_for(
                repository.search_evidence(search_question), timeout=chat_fallback.LOCAL_RETRIEVAL_TIMEOUT_SECONDS,
            )
        else:
            result = await repository.search_evidence(search_question)
    except Exception:
        if development_fallback:
            log.warning("Local retrieval unavailable; using development chat fallback")
            return await _development_response(question, history=history)
        log.exception("OpenSearch passage retrieval lỗi")
        return ChatResponse(
            answer="Kho dữ liệu hiện không khả dụng; tôi chưa thể trả lời có bằng chứng.",
            resolution_status="unavailable", answer_type="insufficient_evidence",
            abstained=True, abstention_reason="service_unavailable",
        )

    query = result.query
    if query.ambiguous:
        return ChatResponse(
            answer="Bạn muốn hỏi về địa điểm nào?", needs_user_choice=True,
            suggestions=query.corrections, resolution_status="ambiguous",
            answer_type="suggestion",
        )
    if not result.evidence:
        return ChatResponse(
            answer="Tôi không tìm thấy bằng chứng phù hợp trong dữ liệu hiện có.",
            resolution_status="not_found", answer_type="insufficient_evidence",
            abstained=True, abstention_reason="insufficient_evidence",
        )

    with rag_observation('context.assembly') as observation:
        context = ' '.join(item.text for item in result.evidence)
        graph_items = []
        if result.graph_context:
            labeled_context = '\n\n'.join(
                f'[Passage {item.id}]\n{item.text}' for item in result.evidence
            )
            header = ('\n\nBỐI CẢNH GRAPHRAG — máy trích xuất, chưa xác minh nội dung. '
                      'Dùng để liên kết ý; đối chiếu các Passage gốc ở trên:\n')
            budget = min(1200, max(0, 4800 - len(labeled_context)))
            lines = []
            for item in result.graph_context:
                line = json.dumps(item, ensure_ascii=False)
                if len(header) + len('\n'.join([*lines, line])) <= budget:
                    lines.append(line)
                    graph_items.append(item)
            if lines:
                context = labeled_context + header + '\n'.join(lines)
        observation.update(output={'context': context, 'graph_context': graph_items}, metadata={
            'context_chars': len(context),
            'selected_passage_ids': [item.id for item in result.evidence],
            'graph_context_count': len(graph_items),
        })

    def generate():
        options = {"history": history} if history else {}
        answer = generate_response(question=query.search_text, context=context, **options)
        return answer, get_generation_details()

    try:
        if development_fallback:
            answer, details = await asyncio.wait_for(
                asyncio.to_thread(generate), timeout=chat_fallback.LOCAL_INFERENCE_TIMEOUT_SECONDS,
            )
            if not answer.strip():
                raise ValueError("Local model returned an empty answer")
        else:
            answer, details = await asyncio.to_thread(generate)
    except Exception:
        if development_fallback:
            log.warning("Local generation unavailable; using development chat fallback")
            return await _development_response(
                question, context=context, sources=[item.to_source() for item in result.evidence], history=history,
            )
        log.exception("LLM generation lỗi")
        raise HTTPException(status_code=503, detail="Model trả lời hiện không khả dụng.") from None

    observe_grounded_qa(
        os.environ.get("OBSERVABILITY_CONTENT_CAPTURE", "metadata"),
        model=details.model, corpus_version="opensearch",
        evidence_ids=[str(item.id) for item in result.evidence],
        token_usage=details.token_usage, grounded=True,
        latency_ms=(time.perf_counter() - started) * 1000,
        correlation_id=correlation_id.get(), prompt=question, evidence=context,
    )
    correction = query.corrections[0] if query.corrections else {}
    return ChatResponse(
        answer=answer, sources=[item.to_source() for item in result.evidence],
        corrected_from=correction.get("original", ""),
        corrected_to=correction.get("suggested", ""),
        intent=",".join(sorted(query.intent)),
        resolution_status="resolved", answer_type="answered",
    )


async def _development_response(
    question: str, *, context: str = "", sources: list[dict] | None = None, history: list[dict] | None = None,
) -> ChatResponse:
    options = {"history": history} if history else {}
    answer = await chat_fallback.development_answer(question, context=context, sources=sources, **options)
    return ChatResponse(**answer.model_dump())
