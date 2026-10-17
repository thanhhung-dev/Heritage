"""Chat grounded in checksum-verified R2 passages indexed in PostgreSQL."""
from __future__ import annotations

import asyncio
import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.llm import generate_response, get_generation_details
from apps.backend.core.observability import correlation_id, observe_grounded_qa
from apps.backend.core.rag import evidence_context
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.services.passages import PassageRepository

log = logging.getLogger(__name__)
router = APIRouter()


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


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    started = time.perf_counter()
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="message trống")

    # All answers require evidence, including requests from older use_rag clients.
    try:
        result = await PassageRepository(db).search_evidence(question)
    except Exception:
        log.exception("R2 passage retrieval lỗi")
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

    context = evidence_context(result.evidence, query)

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
        model=details.model, corpus_version="r2",
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
