"""Chat grounded in complete text chunks retrieved from OpenSearch."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException

from apps.backend.ai.answering.conversation import ConversationAnswer
from apps.backend.api.public.chat.schemas import ChatRequest, ChatResponse
from apps.backend.ai.providers.llm import generate_response, get_generation_details
from apps.backend.common.observability import correlation_id, observe_grounded_qa, rag_observation
from apps.backend.common.search.opensearch import PassageStore, SearchError
from apps.backend.ai.retrieval.passages import EmbeddingError, PassageRepository, PassageSearch, RetrievalQuery

from apps.backend.services.tour_chat import TourChatError, answer_in_area

from apps.backend.api.conversations import get_chat_db, get_conversation_service, mount_conversation_routes
from apps.backend.services.chat_context import question_with_context, retrieval_question

log = logging.getLogger(__name__)
router = APIRouter()


async def get_repository():
    async with PassageStore() as store:
        yield PassageRepository(store)


@router.post("/chat", response_model=ChatResponse, responses={
    504: {"description": "AI vượt quá thời gian chờ 30 giây cho tour có khóa khu vực."},
    500: {"description": "Lỗi retrieval nội bộ; detail chứa code=RETRIEVAL_INTERNAL_ERROR và message."},
    503: {"description": "Lỗi embedding/OpenSearch; detail chứa code=EMBEDDING_FAILED hoặc "
                         "OPENSEARCH_FAILED và message. Lỗi LLM giữ detail dạng chuỗi."},
})
async def chat(req: ChatRequest, repository: PassageRepository = Depends(get_repository)):
    """Hội thoại và hỏi đáp di sản trong tối đa một lượt sinh LLM, không dò lời chào.

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
        try:
            response = await asyncio.wait_for(_chat(req, repository), timeout=30)
        except TimeoutError:
            raise HTTPException(504, "AI phản hồi quá thời gian chờ 30 giây.") from None
        observation.update(output=response.model_dump(), metadata={
            'resolution_status': response.resolution_status,
            'answer_type': response.answer_type,
            'selected_passage_ids': [s['passage_id'] for s in response.sources],
        })
        return response


async def _chat(req: ChatRequest, repository: PassageRepository):
    if req.active_area_id:
        try:
            return ChatResponse(**await answer_in_area(
                req, repository, generate_response, get_generation_details,
            ))
        except TourChatError as error:
            raise HTTPException(status_code=error.status, detail=error.detail) from None
    started = time.perf_counter()
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="message trống")

    # Retrieval remains unchanged; only factual answers require its evidence.
    result = PassageSearch(RetrievalQuery(question), [])
    retrieval_error = None
    try:
        result = await repository.search_evidence(retrieval_question(
            question_with_context(req), req.conversation_context,
        ))
    except EmbeddingError:
        log.exception("Query embedding lỗi")
        retrieval_error = HTTPException(status_code=503, detail={
            "code": "EMBEDDING_FAILED", "message": "Không thể tạo embedding cho câu hỏi.",
        })
    except SearchError:
        log.exception("OpenSearch passage retrieval lỗi")
        retrieval_error = HTTPException(status_code=503, detail={
            "code": "OPENSEARCH_FAILED", "message": "Không thể truy vấn dữ liệu từ OpenSearch.",
        })
    except Exception:
        log.exception("Passage retrieval lỗi nội bộ")
        retrieval_error = HTTPException(status_code=500, detail={
            "code": "RETRIEVAL_INTERNAL_ERROR", "message": "Đã xảy ra lỗi nội bộ khi truy xuất bằng chứng.",
        })

    retrieval_status = ("unavailable" if retrieval_error else
                        "available" if result.evidence else "not_found")
    query = result.query
    if query.ambiguous:
        return ChatResponse(
            answer="Bạn muốn hỏi về địa điểm nào?", needs_user_choice=True,
            suggestions=query.corrections, resolution_status="ambiguous",
            answer_type="suggestion",
        )
    with rag_observation('context.assembly') as observation:
        context = '\n\n'.join(f'[Passage {item.id}]\n{item.text}' for item in result.evidence)
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
        observation.update(output={'context': context, 'graph_context': graph_items}, metadata={
            'context_chars': len(context),
            'selected_passage_ids': [item.id for item in result.evidence],
            'graph_context_count': len(graph_items),
        })

    def generate():
        answer = generate_response(
            question=question, context=context, conversation=True, retrieval_status=retrieval_status,
            **({"history": [item.model_dump() for item in req.conversation_context]} if req.conversation_context else {}),
            **({"scene_context": {"heritage": req.heritage_context, "scene": req.scene_context}}
               if req.heritage_context or req.scene_context else {}),
        )
        return answer, get_generation_details()

    try:
        raw, details = await asyncio.to_thread(generate)
        if details.truncated is True:
            raise ValueError("Incomplete model answer")
        answer = ConversationAnswer.model_validate_json(raw)
        if answer.answer_type == "clarification":
            answer.answer = "Bạn muốn tìm hiểu về di sản hoặc nội dung cụ thể nào?"
        if answer.answer_type == "answered":
            if not result.evidence:
                # Even schema-valid output cannot turn missing evidence into facts.
                answer = ConversationAnswer(
                    answer="Tôi không tìm thấy bằng chứng phù hợp trong dữ liệu hiện có.",
                    answer_type="insufficient_evidence", source_ids=[],
                )
            elif not answer.source_ids or not set(answer.source_ids) <= {str(e.id) for e in result.evidence}:
                raise ValueError("Answer must cite supplied passages")
    except ValueError:
        # Validation errors can contain generated content; do not log that text.
        log.warning("LLM output không hợp lệ hoặc bị cắt")
        raise HTTPException(status_code=503, detail="Model trả lời hiện không khả dụng.") from None
    except Exception:
        log.exception("LLM generation lỗi")
        raise HTTPException(status_code=503, detail="Model trả lời hiện không khả dụng.") from None

    if retrieval_error and answer.answer_type == "insufficient_evidence":
        raise retrieval_error from None
    selected = [item for item in result.evidence if str(item.id) in answer.source_ids]
    observe_grounded_qa(
        os.environ.get("OBSERVABILITY_CONTENT_CAPTURE", "metadata"),
        model=details.model, corpus_version="opensearch",
        evidence_ids=[str(item.id) for item in selected],
        token_usage=details.token_usage, grounded=answer.answer_type == "answered",
        latency_ms=(time.perf_counter() - started) * 1000,
        correlation_id=correlation_id.get(), prompt=question,
        evidence=' '.join(item.text for item in selected),
    )
    correction = query.corrections[0] if query.corrections and selected else {}
    return ChatResponse(
        answer=answer.answer, sources=[item.to_source() for item in selected],
        corrected_from=correction.get("original", ""),
        corrected_to=correction.get("suggested", ""),
        intent=",".join(sorted(query.intent)) if selected else answer.answer_type,
        resolution_status="not_found" if answer.answer_type == "insufficient_evidence" else "resolved",
        answer_type=answer.answer_type,
    )


mount_conversation_routes(router, get_repository, _chat)
