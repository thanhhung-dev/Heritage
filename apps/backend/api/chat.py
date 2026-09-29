"""Chat API backed exclusively by curated PostgreSQL evidence."""
from __future__ import annotations

import logging
import os
import re
import time

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel

from apps.backend.core.fuzzy_match import LOCATION_TYPE_PREFIXES, _without_location_type
from apps.backend.core.rag import retrieve_context
from apps.backend.core.llm import generate_response
from apps.backend.core.textutil import strip_accents, WORD_RE
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.services.kg import KgRepository, EntityCandidate
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)
_MODEL_SOURCE_SUFFIX = re.compile(r"\s*\[?\s*Nguồn\s*:.*$", re.IGNORECASE | re.DOTALL)

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
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message trống")

    try:
        evidence = await KgRepository(db).search_evidence(question)
    except Exception:
        log.exception("PostgreSQL evidence retrieval lỗi")
        return ChatResponse(
            answer="Kho dữ liệu hiện không khả dụng; tôi chưa thể trả lời có bằng chứng.",
            resolution_status="unavailable",
            answer_type="insufficient_evidence",
        )

    if not evidence:
        return ChatResponse(
            answer="Tôi không tìm thấy bằng chứng phù hợp trong dữ liệu hiện có.",
            resolution_status="not_found",
            answer_type="insufficient_evidence",
        )

    context = "\n\n".join(
        (
            f"[{item.evidence_id}]\n"
            f"Tiêu đề: {item.source_title}\n"
            f"URL: {item.source_url}\n"
            f"Nội dung: {item.content}"
        )
        for item in evidence
    )
    try:
        answer = generate_response(question=question, context=context)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}") from exc
    return ChatResponse(answer=answer, sources=sources, answer_type="answered")

    # --- Legacy pipeline retained below for compatibility while callers migrate. ---
    sources: list[dict] = []
    corrections: list[dict] = []
    context = ""
    effective_message = req.message

    if req.use_rag:
        try:
            context, sources, corrections = retrieve_context(req.message)
        except Exception:
            log.exception("retrieval lỗi, trả lời với context rỗng")
            context, sources, corrections = "", [], []

        intro_question = _intro_question_for_bare_entity(req.message, sources)
        if intro_question != req.message:
            effective_message = intro_question
            try:
                intro_context, intro_sources, intro_corrections = retrieve_context(
                    effective_message
                )
                if intro_context.strip() and intro_sources:
                    context = intro_context
                    sources = intro_sources
                    corrections = intro_corrections
            except Exception:
                log.exception("retrieval lại cho tên entity đứng riêng bị lỗi")

        # Khi retrieval thất bại, thử resolve entity từ DB (bao gồm address-based)
        # rồi dùng canonical name để rerun retrieval. Ví dụ:
        # "kể chi tiết về nhà thờ trần phú" → resolve → "Nhà thờ chính tòa Đà Nẵng"
        if not context.strip() or not sources:
            try:
                repo = KgRepository(db)
                resolved = await repo.resolve_entities(req.message, limit=3)

                if len(resolved) == 1:
                    # Single match → dùng canonical name để rerun retrieval
                    canonical = resolved[0].entity.name
                    # Thay phần tên entity trong query bằng canonical name.
                    # Tìm type prefix (nhà thờ, chùa, lăng...) trong query,
                    # rồi replace type prefix + tên sai → canonical name,
                    # giữ lại prefix và suffix.
                    q_stripped = strip_accents(req.message).lower()
                    tokens = WORD_RE.findall(q_stripped)
                    token_spans = [
                        (m.start(), m.end())
                        for m in WORD_RE.finditer(strip_accents(req.message))
                    ]

                    # Tìm type prefix trong tokens
                    replaced = False
                    for prefix_tokens in sorted(
                        LOCATION_TYPE_PREFIXES, key=len, reverse=True
                    ):
                        n = len(prefix_tokens)
                        for i in range(len(tokens) - n + 1):
                            if tuple(tokens[i:i + n]) == prefix_tokens:
                                if i < len(token_spans):
                                    # Vị trí bắt đầu type prefix
                                    entity_start = token_spans[i][0]
                                    # Ước tính entity name end: type prefix tokens
                                    # + core keywords (tên riêng)
                                    end_idx = i + n
                                    # Skip qua tên riêng: tokens cho đến khi
                                    # gặp từ >= 4 chars không phải tên riêng
                                    # hoặc hết query
                                    for j in range(i + n, len(tokens)):
                                        # Giữ lại tokens ngắn hoặc đã biết
                                        # là phần tên riêng
                                        if tokens[j] in {
                                            "co", "gi", "dac", "biet", "o",
                                            "dau", "la", "the", "nao",
                                        }:
                                            end_idx = j
                                            break
                                        end_idx = j + 1

                                    text_prefix = req.message[:entity_start]
                                    if end_idx < len(token_spans):
                                        text_suffix = " " + req.message[
                                            token_spans[end_idx][0]:
                                        ]
                                    else:
                                        text_suffix = ""
                                    effective_message = (
                                        text_prefix + canonical + text_suffix
                                    )
                                    replaced = True
                                    break
                        if replaced:
                            break

                    if not replaced:
                        effective_message = f"Hãy kể chi tiết về {canonical}"

                    log.info(
                        "Entity resolved via DB, rerun retrieval: %s → %s",
                        req.message, effective_message,
                    )
                    try:
                        context, sources, corrections = retrieve_context(effective_message)
                        if context.strip() and sources:
                            corrections = []  # Clear corrections vì đã resolve đúng
                    except Exception:
                        log.exception("rerun retrieval lỗi")

                elif len(resolved) > 1:
                    # Multiple matches → trả suggestions
                    return ChatResponse(
                        answer="",
                        needs_user_choice=True,
                        suggestions=[c.to_dict() for c in resolved[:3]],
                        resolution_status="ambiguous",
                        answer_type="suggestion",
                    )
            except Exception:
                log.exception("DB entity resolution fallback lỗi")

    notice, corrected_from, corrected_to, needs_user_choice, suggestions = (
        _resolve_correction(corrections)
    )

    if needs_user_choice:
        return ChatResponse(
            answer="",
            sources=[],
            needs_user_choice=True,
            suggestions=suggestions,
        )

    if not context.strip() or not sources:
        return ChatResponse(
            answer=(
                "Tôi không tìm thấy nguồn phù hợp trong dữ liệu hiện có, nên chưa "
                "thể trả lời câu hỏi này mà không suy đoán."
            ),
            sources=[],
            answer_type="insufficient_evidence",
        )

    llm_question = effective_message
    if corrected_from and corrected_to:
        llm_question = effective_message.replace(corrected_from, corrected_to)
        remaining = effective_message.replace(corrected_from, "").strip(" \t\r\n?!.,")
        if not remaining:
            llm_question = f"Hãy giới thiệu về {corrected_to}."

    try:
        answer = generate_response(
            question=llm_question,
            context=context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    return ChatResponse(
        answer=answer,
        sources=[item.to_source() for item in evidence],
        resolution_status="resolved",
        answer_type="answered",
    )
