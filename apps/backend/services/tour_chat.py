"""Area-locked tour application service; independent of the HTTP adapter."""
from __future__ import annotations

import asyncio
import json
import re

from apps.backend.ai.answering.conversation import (
    ConversationAnswer, append_graph_follow_up_hint, grounded_source_ids,
    dialogue_turns, is_dialogue_question, is_social_turn, prior_user_questions, visible_answer,
)
from apps.backend.common.config import chat_timeout_seconds
from apps.backend.services.heritage_graph import artifact_title_from_data, ordered_entity_follow_ups
from apps.backend.services.tour_guide import GUIDE_STORIES, TourFocus, guide_stories
from apps.backend.services.tour_scope import (
    allowed_output, allowed_tour_output, follow_up_questions, normalized,
    question_outside_area, resolve_area, scoped_missing, scoped_refusal,
)
from apps.backend.services.web_research import WEB_LABEL, research_heritage


class TourChatError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


async def answer_in_area(request, repository, generate, generation_details, *, reply_context=None) -> dict:
    timeout = chat_timeout_seconds()
    try:
        return await asyncio.wait_for(
            _answer_in_area(request, repository, generate, generation_details, reply_context=reply_context),
            timeout=timeout,
        )
    except TimeoutError as error:
        raise TourChatError(504, f"AI phản hồi quá thời gian chờ {timeout:g} giây. Vui lòng thử lại.") from error


async def _answer_in_area(request, repository, generate, generation_details, *, reply_context=None) -> dict:
    area = resolve_area(request.active_area_id)
    question = request.message.strip()
    if not question:
        raise TourChatError(400, "message trống")

    history = [item.model_dump() for item in request.conversation_context]
    user_history = prior_user_questions(history)
    dialogue = dialogue_turns(history)
    selected_marker = bool(reply_context and reply_context.highlight_id is not None)
    links = reply_context.passage_links if selected_marker else None
    focus = TourFocus(title=reply_context.highlight_title or "Điểm đang chọn") if selected_marker else None
    unmapped_marker = selected_marker and not links
    destination = question_outside_area(question, area)
    social = is_social_turn(question)

    def response(text, kind, sources=(), questions=(), graph_context=None, evidence=(), *, story_complete=True):
        del questions
        if any(source.get("source_type") == "web" for source in sources):
            text = f"{WEB_LABEL}\n\n{text}"
            story_complete = False
        snapshot = reply_context.model_copy(update={
            "story_id": reply_context.story_id if kind == "answered" and story_complete else None,
        }).model_dump() if reply_context else None
        artifact = None if unmapped_marker else artifact_title_from_data(
            focus_title=focus.title if focus else None,
            graph_context=graph_context, evidence=evidence,
        )
        if kind in {"out_of_scope", "insufficient_evidence"}:
            scoped = []
        else:
            related = [] if unmapped_marker else ordered_entity_follow_ups(
                question, area_title=area.title, artifact_title=artifact,
            )
            asked_norm = normalized(question)
            scoped = [
                item for item in follow_up_questions(
                    related, area, fallback=not selected_marker or kind == "answered",
                    fallback_questions=focus.questions() if focus else None,
                ) if normalized(item) != asked_norm
            ]
        return {
            "answer": text, "answer_type": kind, "sources": list(sources),
            "active_area_id": area.id,
            "reply_context": snapshot,
            "follow_up_questions": scoped[:2],
            "resolution_status": "not_found" if kind == "insufficient_evidence" else "resolved",
        }

    scene_hint = request.scene_context
    if reply_context:
        scene_hint = {"title": reply_context.scene_title, "key": reply_context.scene_key,
                      "mode": reply_context.mode, "highlight_title": reply_context.highlight_title or "",
                      "narration": request.tour_context.narration}
        # Only server-owned story labels enter this hint; client history is not evidence.
        scene_hint["completed_stories"] = "; ".join(
            story.label for (area_id, _, _), stories in GUIDE_STORIES.items() if area_id == area.id
            for story in stories if story.id in request.tour_context.completed_story_ids
        )[:200]

    evidence = []
    graph_context = []
    if not social and destination is None and not unmapped_marker:
        search_question = question
        reference = re.match(
            r"^(?:(?:the|con) )?(ong ay|ba ay|nguoi ay|ho|no|lang kia)\b",
            normalized(question),
        )
        if reference and user_history:
            search_question = (
                "Câu hỏi trước của người dùng: " + " | ".join(user_history[-3:])
                + "\nCâu hỏi hiện tại: " + question
            )
        scene_title = scene_hint.get("title") if isinstance(scene_hint, dict) else None
        scene_reference = re.search(
            r"\b(?:(?:bia|vat|co vat) (?:nay|day|do|gi)|o day|"
            r"(?:noi|cho|canh|diem|cong trinh|cai) (?:nay|day|do)|"
            r"(?:dang xem|dang an vao) (?:gi|co vat)?|day la (?:bia|vat|co vat))\b",
            normalized(question),
        )
        if focus:
            search_question += f"\nĐiểm đang chọn: {focus.title}"
        elif ((scene_reference or (reply_context and reply_context.story_id))
              and isinstance(scene_title, str) and scene_title.strip() and allowed_output(scene_title)):
            search_question += f"\nCảnh đang xem: {scene_title[:200]}"
            if reply_context and reply_context.highlight_title:
                search_question += f"\nĐiểm được chọn: {reply_context.highlight_title}"
        try:
            search_options = {"active_area_id": area.id}
            if links is not None:
                search_options["passage_links"] = links
            result = await repository.search_evidence(search_question, **search_options)
        except Exception as error:
            # Never replace unavailable area evidence with unscoped/model-memory facts.
            raise TourChatError(503, "Kho dữ liệu của khu vực đang tham quan hiện không khả dụng.") from error
        evidence = [
            item for item in result.evidence
            if getattr(item, "active_area_id", None) == area.id
            and (links is None or str(item.id) in links)
        ]
        graph_context = result.graph_context

    # Keep an independent, bounded KB set for the fallback path. The mixed model
    # context reserves room for web evidence, but must not discard useful KB text.
    kb_fallback_evidence = []
    kb_fallback_size = 0
    for item in evidence:
        block = f"[Passage {item.id}]\n{item.text}"
        if kb_fallback_size + len(block) + 2 <= 4800:
            kb_fallback_evidence.append(item)
            kb_fallback_size += len(block) + 2

    web_evidence = ()
    if not social and destination is None and not is_dialogue_question(question):
        research = await research_heritage(
            question, area.title, area.names, area_id=area.id,
            context="\n\n".join(item.text for item in evidence)[:4800],
            focus=focus.title if focus else "", generate=generate, generation_details=generation_details,
        )
        web_evidence = research.evidence
    if unmapped_marker and not web_evidence:
        return response(scoped_missing(area), "insufficient_evidence")

    # Bound whole evidence chunks; never accidentally send unbounded adapter output.
    selected = []
    context = ""
    for item in evidence:
        block = f"[Passage {item.id}]\n{item.text}"
        if len(context) + len(block) + 2 <= (2000 if web_evidence else 4800):
            selected.append(item)
            context += ("\n\n" if context else "") + block
    for item in web_evidence:
        block = f"[Passage {item.id}]\n{item.text}"
        if len(context) + len(block) + 2 <= 4800:
            selected.append(item)
            context += ("\n\n" if context else "") + block
    evidence = selected
    if selected_marker and not evidence and not social and destination is None and not dialogue:
        return response(scoped_missing(area), "insufficient_evidence")
    ids = {str(item.id) for item in evidence}
    story = next((story for story in guide_stories(area.id, reply_context.scene_title, reply_context.highlight_title)
                  if story.id == reply_context.story_id), None) if reply_context else None
    story_evidence_missing = bool(story and not set(story.source_ids) <= ids)

    accepted_graph = []
    for item in graph_context:
        lineage = {str(value) for value in item.get("source_passage_ids", [])}
        block = json.dumps(item, ensure_ascii=False)
        if lineage and lineage <= ids and allowed_output(block) and len(context) + len(block) + 2 <= 4800:
            context += "\n\n" + block
            accepted_graph.append(item)
    context = append_graph_follow_up_hint(context, accepted_graph)
    def repeats_other_turn(text: str) -> bool:
        last_user = next((item["content"] for item in reversed(dialogue) if item["role"] == "user"), "")
        last_assistant = next((item["content"] for item in reversed(dialogue) if item["role"] == "assistant"), "")
        if not last_assistant or normalized(question) == normalized(last_user):
            return False
        return normalized(text) == normalized(last_assistant)

    def infer(suffix: str = ""):
        asked = question if not suffix else f"{question}\n\n{suffix}"
        raw = generate(
            question=asked, context=context, conversation=True,
            retrieval_status="available" if evidence else "not_found",
            active_area_id=area.id, user_history=user_history, dialogue=dialogue,
            artifact_title=focus.title if focus else None,
        )
        return raw, generation_details()

    def related_or_missing():
        if destination is not None:
            return response(scoped_refusal(area, destination), "out_of_scope")
        # Retrieval already enforces the area and reviewed highlight links. Even
        # a partial KB match is useful; preserve it if the mixed context reserved
        # space for web evidence and the model could not produce a cited answer.
        for item in (*kb_fallback_evidence, *web_evidence):
            excerpts = [
                part.strip() for part in re.split(r"(?<=[.!?])\s+|[\r\n]+", item.text)
                if part.strip() and allowed_tour_output(part.strip(), "answered", area)
            ]
            if not excerpts:
                continue
            text = (
                "Tư liệu hiện có chưa trả lời trực tiếp đầy đủ câu hỏi này. "
                "Mình tìm được thông tin liên quan:\n\n" + " ".join(excerpts)
            )
            return response(
                text, "answered", [item.to_source()], evidence=[item], story_complete=False,
            )
        return response(scoped_missing(area), "insufficient_evidence")

    def parse(raw, details):
        if details.truncated is True:
            raise ValueError("Truncated answer")
        payload = json.loads(raw)
        if (
            isinstance(payload, dict)
            and payload.get("answer_type") == "insufficient_evidence"
            and payload.get("source_ids")
        ):
            payload["answer_type"] = "answered"
            raw = json.dumps(payload, ensure_ascii=False)
        return ConversationAnswer.model_validate_json(raw)

    try:
        answer = parse(*await asyncio.to_thread(infer))
    except Exception:
        return related_or_missing()

    if social:
        if answer.answer_type == "conversation" and allowed_tour_output(answer.answer, "conversation", area):
            return response(answer.answer, "conversation", questions=answer.follow_up_questions)
        return response(
            f"Mình ở {area.title} với bạn. Bạn muốn hỏi gì ở đây?",
            "conversation",
        )

    if destination is not None:
        if (answer.answer_type == "out_of_scope"
                and allowed_tour_output(answer.answer, "out_of_scope", area, destination=destination)):
            return response(answer.answer, "out_of_scope", questions=answer.follow_up_questions)
        return response(scoped_refusal(area, destination), "out_of_scope")
    if story_evidence_missing and answer.answer_type != "conversation":
        return related_or_missing()

    if (
        not is_dialogue_question(question)
        and (
            answer.answer_type == "conversation"
            or repeats_other_turn(answer.answer)
        )
    ):
        try:
            answer = parse(*await asyncio.to_thread(lambda: infer(
                "Câu này hỏi tư liệu của địa điểm đang xem, không hỏi lại hội thoại. "
                "answer_type phải là answered hoặc insufficient_evidence. Không chép câu trả lời trước."
            )))
        except Exception:
            return related_or_missing()
        if answer.answer_type == "conversation" or repeats_other_turn(answer.answer):
            return related_or_missing()


    if answer.answer_type in {"answered", "insufficient_evidence"}:
        cited = grounded_source_ids(answer.source_ids, ids)
        spoken = visible_answer(answer.answer)
        story_uncited = bool(story and not set(story.source_ids) <= set(cited))
        if not spoken:
            return related_or_missing()
        if cited and not story_uncited and allowed_tour_output(spoken, "answered", area):
            sources = [item.to_source() for item in evidence if str(item.id) in cited]
            return response(
                spoken, "answered", sources, questions=answer.follow_up_questions,
                graph_context=accepted_graph, evidence=evidence,
            )
        return related_or_missing()
    if answer.answer_type == "conversation":
        if not is_dialogue_question(question):
            return related_or_missing()
        if allowed_tour_output(answer.answer, "conversation", area):
            return response(answer.answer, "conversation", questions=answer.follow_up_questions)
        return response("Mình không nhớ lượt trước để nhắc lại.", "conversation")
    if not allowed_tour_output(answer.answer, "out_of_scope", area):
        return response(scoped_refusal(area), "out_of_scope")
    return response(answer.answer, "out_of_scope", questions=answer.follow_up_questions)
