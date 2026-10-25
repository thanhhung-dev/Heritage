"""Chat grounded in complete text chunks retrieved from OpenSearch."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from apps.backend.core.llm import generate_response, get_generation_details
from apps.backend.core.observability import correlation_id, observe_grounded_qa, rag_observation
from apps.backend.core.search import PassageStore
from apps.backend.services.passages import PassageRepository
from apps.backend.core.security import get_current_user
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.schemas.chat import ChatMessageCreate, ChatResponse as PersistedChatResponse
from apps.backend.services.conversations import ChatServiceError, ConversationService, GroundedAnswer

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


class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = Field(default_factory=list)
    corrected_from: str = ""
    corrected_to: str = ""
    needs_user_choice: bool = False
    suggestions: list[dict] = Field(default_factory=list)
    entity_id: str | None = None
    intent: str | None = None
    resolution_status: str | None = None
    answer_type: str | None = None


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
    async def answerer(question: str) -> GroundedAnswer:
        # Reuse the existing retrieval, evidence gate, generation and observability.
        try:
            response = await chat(ChatRequest(message=question), repository)
        except HTTPException:
            raise ChatServiceError("inference", "Hệ thống AI hiện không thể trả lời. Vui lòng thử lại.") from None
        return GroundedAnswer(
            answer=response.answer, sources=response.sources,
            resolution_status=response.resolution_status, answer_type=response.answer_type,
        )

    try:
        return await service.send(request, account_id, answerer)
    except ChatServiceError as error:
        raise conversation_http_error(error) from None
    except Exception:
        log.exception("Không thể lưu cuộc trò chuyện")
        raise HTTPException(status_code=500, detail="Không thể xử lý cuộc trò chuyện. Vui lòng thử lại.") from None


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, repository: PassageRepository = Depends(get_repository)):
    with rag_observation('rag.request', input={'question': req.message}, metadata={
        'correlation_id': correlation_id.get(), 'corpus_version': 'opensearch',
        'grounding_verified': False,
    }) as observation:
        response = await _chat(req, repository)
        observation.update(output=response.model_dump(), metadata={
            'resolution_status': response.resolution_status,
            'answer_type': response.answer_type,
            'selected_passage_ids': [s['passage_id'] for s in response.sources],
        })
        return response


async def _chat(req: ChatRequest, repository: PassageRepository):
    started = time.perf_counter()
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="message trống")

    # All answers require evidence, including requests from older use_rag clients.
    try:
        result = await repository.search_evidence(question)
    except Exception:
        log.exception("OpenSearch passage retrieval lỗi")
        return ChatResponse(
            answer="Kho dữ liệu hiện không khả dụng; tôi chưa thể trả lời có bằng chứng.",
            resolution_status="unavailable", answer_type="insufficient_evidence",
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
        answer = generate_response(question=query.search_text, context=context)
        return answer, get_generation_details()

    try:
        answer, details = await asyncio.to_thread(generate)
    except Exception:
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
