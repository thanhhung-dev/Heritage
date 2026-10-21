"""Chat grounded in complete text chunks retrieved from OpenSearch."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException

from apps.backend.api.public.chat.schemas import ChatRequest, ChatResponse
from apps.backend.ai.providers.llm import generate_response, get_generation_details
from apps.backend.common.observability import correlation_id, observe_grounded_qa, rag_observation
from apps.backend.common.search.opensearch import PassageStore
from apps.backend.ai.retrieval.passages import PassageRepository

log = logging.getLogger(__name__)
router = APIRouter()


async def get_repository():
    async with PassageStore() as store:
        yield PassageRepository(store)


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
        log.error("OpenSearch passage retrieval lỗi", exc_info=False)
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
