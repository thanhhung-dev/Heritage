"""Chat grounded in complete text chunks retrieved from OpenSearch."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.backend.ai.answering.conversation import (
    ConversationAnswer, append_graph_follow_up_hint, related_follow_ups, evidence_cite_id, grounded_source_ids,
    dialogue_turns, is_social_turn, prior_user_questions, rewrite_followup, visible_answer,
)
from apps.backend.api.public.chat.schemas import ChatRequest, ChatResponse
from apps.backend.common.config import chat_timeout_seconds
from apps.backend.ai.providers.llm import generate_response, get_generation_details
from apps.backend.common.observability import correlation_id, observe_grounded_qa, rag_observation
from apps.backend.common.search.opensearch import PassageStore, SearchError
from apps.backend.ai.retrieval.passages import EmbeddingError, PassageRepository, PassageSearch, RetrievalQuery

from apps.backend.services.tour_chat import TourChatError, answer_in_area

from apps.backend.api.conversations import abort_llama_on_disconnect, get_chat_db, get_conversation_service, mount_conversation_routes, validated_tour_context
from apps.backend.services.chat_context import question_with_context

log = logging.getLogger(__name__)
router = APIRouter()


async def get_repository():
    async with PassageStore() as store:
        yield PassageRepository(store)


@router.post("/chat", response_model=ChatResponse, responses={
    504: {"description": "AI vượt CHAT_TIMEOUT_SECONDS (mặc định 120 giây)."},
    500: {"description": "Lỗi retrieval nội bộ; detail chứa code=RETRIEVAL_INTERNAL_ERROR và message."},
    503: {"description": "Lỗi embedding/OpenSearch; detail chứa code=EMBEDDING_FAILED hoặc "
                         "OPENSEARCH_FAILED và message. Lỗi LLM giữ detail dạng chuỗi."},
})
async def chat(req: ChatRequest, request: Request, repository: PassageRepository = Depends(get_repository)):
    """Hỏi đáp di sản; chat có area và lịch sử thêm một lượt phân giải câu hỏi.

    `conversation` và `out_of_scope` không có sources. `answered` chỉ trả sources
    được model trích và backend kiểm tra ID thuộc các Passage đã cung cấp.
    Không có bằng chứng: `insufficient_evidence`, resolution_status=`not_found`.
    Retrieval lỗi vẫn cho phép hội thoại; yêu cầu kiến thức thiếu bằng chứng giữ
    lỗi 500/503 tương ứng. LLM lỗi, JSON sai hoặc bị cắt: 503, không gọi lại model.
    `use_rag=false` không cho phép trả lời dữ kiện ngoài nguồn. JSON nội bộ không
    được gửi ra client; các trường response hiện có được giữ nguyên.
    """
    with rag_observation('rag.request', input={'question': req.message}, metadata={
        'correlation_id': correlation_id.get(), 'corpus_version': 'opensearch',
        'grounding_verified': False,
    }) as observation:
        timeout = chat_timeout_seconds()
        try:
            async with abort_llama_on_disconnect(request):
                response = await asyncio.wait_for(_chat(req, repository), timeout=timeout)
        except TimeoutError:
            raise HTTPException(504, f"AI phản hồi quá thời gian chờ {timeout:g} giây.") from None
        observation.update(output=response.model_dump(), metadata={
            'resolution_status': response.resolution_status,
            'answer_type': response.answer_type,
            'selected_passage_ids': [s['passage_id'] for s in response.sources],
        })
        return response


async def _chat(req: ChatRequest, repository: PassageRepository):
    if req.active_area_id:
        context = await validated_tour_context(req)
        try:
            return ChatResponse(**await answer_in_area(
                req, repository, generate_response, get_generation_details, reply_context=context,
            ))
        except TourChatError as error:
            raise HTTPException(status_code=error.status, detail=error.detail) from None
    started = time.perf_counter()
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="message trống")
    if is_social_turn(question):
        return ChatResponse(
            answer="Mình là trợ lý AI HeritageGraph.",
            answer_type="conversation", sources=[], resolution_status="resolved",
        )

    history = [item.model_dump() for item in req.conversation_context]
    dialogue = dialogue_turns(history)
    asked = question
    if prior_user_questions(history):
        asked = await asyncio.to_thread(rewrite_followup, question, history, generate_response)
    search_text = asked if asked != question else question_with_context(req)

    # Retrieval remains unchanged; only factual answers require its evidence.
    result = PassageSearch(RetrievalQuery(asked), [])
    try:
        result = await repository.search_evidence(search_text)
    except EmbeddingError:
        log.exception("Query embedding lỗi")
        raise HTTPException(status_code=503, detail={
            "code": "EMBEDDING_FAILED", "message": "Không thể tạo embedding cho câu hỏi.",
        }) from None
    except SearchError:
        log.exception("OpenSearch passage retrieval lỗi")
        raise HTTPException(status_code=503, detail={
            "code": "OPENSEARCH_FAILED", "message": "Không thể truy vấn dữ liệu từ OpenSearch.",
        }) from None
    except Exception:
        log.exception("Passage retrieval lỗi nội bộ")
        raise HTTPException(status_code=500, detail={
            "code": "RETRIEVAL_INTERNAL_ERROR", "message": "Đã xảy ra lỗi nội bộ khi truy xuất bằng chứng.",
        }) from None

    query = result.query
    if query.ambiguous:
        return ChatResponse(
            answer="Bạn muốn hỏi về địa điểm nào?", needs_user_choice=True,
            suggestions=query.corrections, resolution_status="ambiguous",
            answer_type="suggestion",
        )
    missing = "Tôi không tìm thấy bằng chứng phù hợp trong dữ liệu hiện có."
    if not result.evidence:
        return ChatResponse(
            answer=missing, sources=[], resolution_status="not_found",
            answer_type="insufficient_evidence",
        )
    with rag_observation('context.assembly') as observation:
        context = '\n\n'.join(f'[Passage {evidence_cite_id(item)}]\n{item.text}' for item in result.evidence)
        graph_items = []
        if result.graph_context:
            header = ('\n\nBỐI CẢNH GRAPHRAG — máy trích xuất, chưa xác minh nội dung. '
                      'Dùng để liên kết ý; đối chiếu các Passage gốc ở trên:\n')
            budget = min(1200, max(0, 4800 - len(context)))
            lines = []
            for item in result.graph_context:
                line = json.dumps(item, ensure_ascii=False)
                if len(header) + len('\n'.join([*lines, line])) <= budget:
                    lines.append(line)
                    graph_items.append(item)
            if lines:
                context += header + '\n'.join(lines)
        context = append_graph_follow_up_hint(context, result.graph_context)
        observation.update(output={'context': context, 'graph_context': graph_items}, metadata={
            'context_chars': len(context),
            'selected_passage_ids': [item.id for item in result.evidence],
            'graph_context_count': len(graph_items),
        })

    def generate():
        raw = generate_response(
            question=asked, context=context, conversation=True, retrieval_status="available",
            dialogue=dialogue,
        )
        return raw, get_generation_details()

    try:
        raw, details = await asyncio.to_thread(generate)
        if details.truncated is True:
            raise ValueError("Incomplete model answer")
        parsed = ConversationAnswer.model_validate_json(raw)
    except ValueError:
        # Validation errors can contain generated content; do not log that text.
        log.warning("LLM output không hợp lệ hoặc bị cắt")
        raise HTTPException(status_code=503, detail="Model trả lời hiện không khả dụng.") from None
    except Exception:
        log.exception("LLM generation lỗi")
        raise HTTPException(status_code=503, detail="Model trả lời hiện không khả dụng.") from None

    cited = grounded_source_ids(parsed.source_ids, {evidence_cite_id(item) for item in result.evidence})
    if not cited:
        return ChatResponse(
            answer=missing, sources=[], resolution_status="not_found",
            answer_type="insufficient_evidence",
        )
    selected = [item for item in result.evidence if evidence_cite_id(item) in cited]
    observe_grounded_qa(
        os.environ.get("OBSERVABILITY_CONTENT_CAPTURE", "metadata"),
        model=details.model, corpus_version="opensearch",
        evidence_ids=[str(item.id) for item in selected],
        token_usage=details.token_usage, grounded=True,
        latency_ms=(time.perf_counter() - started) * 1000,
        correlation_id=correlation_id.get(), prompt=question,
        evidence=' '.join(item.text for item in selected),
    )
    correction = query.corrections[0] if query.corrections and selected else {}
    return ChatResponse(
        answer=visible_answer(parsed.answer), sources=[item.to_source() for item in selected],
        corrected_from=correction.get("original", ""),
        corrected_to=correction.get("suggested", ""),
        intent=",".join(sorted(query.intent)) if selected else "",
        resolution_status="resolved",
        answer_type="answered",
        follow_up_questions=related_follow_ups(
            parsed.follow_up_questions, asked,
            graph_context=result.graph_context, evidence=selected,
        ),
    )


mount_conversation_routes(router, get_repository, _chat)
