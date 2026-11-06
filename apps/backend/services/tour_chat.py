"""Area-locked tour application service; independent of the HTTP adapter."""
from __future__ import annotations

import asyncio
import json

from apps.backend.ai.answering.conversation import ConversationAnswer
from apps.backend.services.tour_scope import (
    allowed_output, follow_up_questions, mentions_foreign_site, normalized,
    question_outside_area, resolve_area, scoped_missing, scoped_refusal,
)


class TourChatError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


async def answer_in_area(request, repository, generate, generation_details) -> dict:
    area = resolve_area(request.active_area_id)

    def response(text, kind, sources=(), questions=()):
        return {
            "answer": text, "answer_type": kind, "sources": list(sources),
            "active_area_id": area.id,
            "follow_up_questions": follow_up_questions(list(questions), area),
            "resolution_status": "not_found" if kind == "insufficient_evidence" else "resolved",
        }

    question = request.message.strip()
    if not question:
        raise TourChatError(400, "message trống")
    if question_outside_area(question, area):
        return response(scoped_refusal(area), "out_of_scope")
    if normalized(question) in {"hi", "hello", "xin chao", "chao", "cam on", "ban la ai"}:
        return response(f"Mình là trợ lý AI HeritageGraph, đồng hành cùng bạn tại {area.title}. "
                        "Bạn muốn tìm hiểu điều gì trong khu vực đang tham quan?", "conversation")
    try:
        result = await repository.search_evidence(question, active_area_id=area.id)
    except Exception as error:
        # Never replace unavailable area evidence with unscoped/model-memory facts.
        raise TourChatError(503, "Kho dữ liệu của khu vực đang tham quan hiện không khả dụng.") from error
    evidence = [item for item in result.evidence
                if getattr(item, "active_area_id", None) == area.id
                and not mentions_foreign_site(item.text + " " + getattr(item, "location_note", ""), area)]
    if not evidence:
        return response(scoped_missing(area), "insufficient_evidence")
    # Bound whole evidence chunks; never accidentally send unbounded adapter output.
    selected = []
    context = ""
    for item in evidence:
        block = f"[Passage {item.id}]\n{item.text}"
        if len(context) + len(block) + 2 <= 4800:
            selected.append(item)
            context += ("\n\n" if context else "") + block
    evidence = selected
    if not evidence:
        return response(scoped_missing(area), "insufficient_evidence")
    ids = {str(item.id) for item in evidence}
    for item in result.graph_context:
        lineage = {str(value) for value in item.get("source_passage_ids", [])}
        block = json.dumps(item, ensure_ascii=False)
        if lineage and lineage <= ids and allowed_output(block, area) and len(context) + len(block) + 2 <= 4800:
            context += "\n\n" + block

    def infer():
        raw = generate(question=question, context=context, conversation=True,
                       retrieval_status="available", active_area_id=area.id,
                       history=[item.model_dump() for item in request.conversation_context])
        return raw, generation_details()

    try:
        raw, details = await asyncio.wait_for(asyncio.to_thread(infer), timeout=30)
        if details.truncated is True:
            raise ValueError("Truncated answer")
        answer = ConversationAnswer.model_validate_json(raw)
        if answer.answer_type == "answered" and (not answer.source_ids or not set(answer.source_ids) <= ids):
            raise ValueError("Unverified citations")
    except TimeoutError as error:
        raise TourChatError(504, "AI phản hồi quá thời gian chờ. Vui lòng thử lại.") from error
    except Exception as error:
        raise TourChatError(503, "Model trả lời hiện không khả dụng.") from error
    if not allowed_output(answer.answer, area) or answer.answer_type == "out_of_scope":
        return response(scoped_refusal(area), "out_of_scope")
    if answer.answer_type != "answered":
        # A model cannot relabel uncited historical claims as social conversation.
        return response(scoped_missing(area), "insufficient_evidence")
    sources = [item.to_source() for item in evidence if str(item.id) in answer.source_ids]
    return response(answer.answer, "answered", sources, answer.follow_up_questions)
