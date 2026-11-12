"""Area-locked tour application service; independent of the HTTP adapter."""
from __future__ import annotations

import asyncio
import json

from apps.backend.ai.answering.conversation import ConversationAnswer
from apps.backend.common.config import chat_timeout_seconds
from apps.backend.services.chat_context import retrieval_question
from apps.backend.services.tour_guide import GUIDE_STORIES, guide_stories
from apps.backend.services.tour_scope import (
    allowed_output, follow_up_questions, mentions_foreign_site, normalized,
    question_outside_area, resolve_area, scoped_missing, scoped_refusal,
)


class TourChatError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


async def answer_in_area(request, repository, generate, generation_details, *, reply_context=None) -> dict:
    area = resolve_area(request.active_area_id)

    def response(text, kind, sources=(), questions=()):
        snapshot = reply_context.model_copy(update={
            "story_id": reply_context.story_id if kind == "answered" else None,
        }).model_dump() if reply_context else None
        return {
            "answer": text, "answer_type": kind, "sources": list(sources),
            "active_area_id": area.id,
            "reply_context": snapshot,
            "follow_up_questions": [] if reply_context else follow_up_questions(list(questions), area),
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
    safe_history = [item for item in request.conversation_context if not question_outside_area(item.content, area)]
    scene_hint = request.scene_context
    if reply_context:
        scene_hint = {"title": reply_context.scene_title, "key": reply_context.scene_key,
                      "mode": reply_context.mode, "highlight_title": reply_context.highlight_title or "",
                      "narration": request.tour_context.narration}
        # IDs are filtered through the editorial registry; client memory cannot
        # introduce facts or instructions into the prompt.
        scene_hint["completed_stories"] = "; ".join(
            story.label for (area_id, _, _), stories in GUIDE_STORIES.items() if area_id == area.id
            for story in stories if story.id in request.tour_context.completed_story_ids
        )[:200]
    try:
        scene_title = scene_hint.get("title") if isinstance(scene_hint, dict) else None
        if isinstance(scene_title, str) and scene_title.strip() and allowed_output(scene_title, area):
            search_question = f"{retrieval_question(question, safe_history)}\nCảnh đang xem: {scene_title[:200]}"
            if reply_context and reply_context.highlight_title:
                search_question += f"\nĐiểm được chọn: {reply_context.highlight_title}"
        else:
            search_question = retrieval_question(question, safe_history)
        result = await repository.search_evidence(search_question, active_area_id=area.id)
    except Exception as error:
        # Never replace unavailable area evidence with unscoped/model-memory facts.
        raise TourChatError(503, "Kho dữ liệu của khu vực đang tham quan hiện không khả dụng.") from error
    evidence = [item for item in result.evidence
                if getattr(item, "active_area_id", None) == area.id
                and not mentions_foreign_site(item.text + " " + getattr(item, "location_note", "")
                                              + " " + getattr(item, "source_url", ""), area)]
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
    story = next((story for story in guide_stories(area.id, reply_context.scene_title, reply_context.highlight_title)
                  if story.id == reply_context.story_id), None) if reply_context else None
    if story and not set(story.source_ids) <= ids:
        return response(scoped_missing(area), "insufficient_evidence")
    for item in result.graph_context:
        lineage = {str(value) for value in item.get("source_passage_ids", [])}
        block = json.dumps(item, ensure_ascii=False)
        if lineage and lineage <= ids and allowed_output(block, area) and len(context) + len(block) + 2 <= 4800:
            context += "\n\n" + block

    def infer():
        raw = generate(question=question, context=context, conversation=True,
                       retrieval_status="available", active_area_id=area.id,
                       history=[item.model_dump() for item in safe_history],
                       scene_context=scene_hint)
        return raw, generation_details()

    timeout = chat_timeout_seconds()
    try:
        raw, details = await asyncio.wait_for(asyncio.to_thread(infer), timeout=timeout)
        if details.truncated is True:
            raise ValueError("Truncated answer")
        answer = ConversationAnswer.model_validate_json(raw)
        if answer.answer_type == "answered" and (not answer.source_ids or not set(answer.source_ids) <= ids):
            raise ValueError("Unverified citations")
        if story and answer.answer_type == "answered" and not set(story.source_ids) <= set(answer.source_ids):
            raise ValueError("Story must cite its reviewed sources")
    except TimeoutError as error:
        raise TourChatError(504, f"AI phản hồi quá thời gian chờ {timeout:g} giây. Vui lòng thử lại.") from error
    except Exception as error:
        raise TourChatError(503, "Model trả lời hiện không khả dụng.") from error
    if not allowed_output(answer.answer, area) or answer.answer_type == "out_of_scope":
        return response(scoped_refusal(area), "out_of_scope")
    if answer.answer_type != "answered":
        if answer.answer_type == "clarification":
            subject = reply_context.highlight_title or reply_context.scene_title if reply_context else area.title
            return response(f"Bạn đang hỏi về {subject}, hay chủ đề vừa trao đổi? Bạn nói rõ đối tượng giúp mình nhé.", "clarification")
        # A model cannot relabel uncited historical claims as social conversation.
        return response(scoped_missing(area), "insufficient_evidence")
    sources = [item.to_source() for item in evidence if str(item.id) in answer.source_ids]
    return response(answer.answer, "answered", sources, answer.follow_up_questions)
