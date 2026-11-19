"""Area-locked tour application service; independent of the HTTP adapter."""
from __future__ import annotations

import asyncio
import json
import re

from apps.backend.ai.answering.conversation import (
    ConversationAnswer, append_graph_follow_up_hint, related_follow_ups, grounded_source_ids,
    is_social_turn, prior_user_questions,
)
from apps.backend.common.config import chat_timeout_seconds
from apps.backend.services.tour_guide import (
    GUIDE_STORIES, TourArtifact, guide_stories, marker_is_verified_non_artifact,
    referenced_tour_artifacts, tour_artifact,
)
from apps.backend.services.tour_scope import (
    allowed_output, allowed_tour_output, follow_up_questions, normalized,
    question_outside_area, resolve_area, scoped_missing, scoped_refusal,
)


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
    artifact = None
    if reply_context and reply_context.artifact_key:
        artifact = TourArtifact(
            id=reply_context.artifact_key,
            title=reply_context.highlight_title or reply_context.artifact_key,
            aliases=(),
            source_ids=frozenset(),
            artifact_key=reply_context.artifact_key,
        )
    elif reply_context:
        # Legacy in-code entries remain only for compatibility with old fixtures.
        artifact = tour_artifact(area.id, reply_context.scene_id, reply_context.highlight_id)
    selected_marker = bool(reply_context and reply_context.highlight_id is not None)
    verified_non_artifact = bool(
        selected_marker and marker_is_verified_non_artifact(
            area.id, reply_context.scene_id, reply_context.highlight_id,
        )
    )
    marker_reference = bool(re.search(
        r"\b(?:(?:bia|vat|co vat) (?:nay|day|do|gi)|o day|"
        r"(?:noi|cho|canh|diem|cong trinh|cai) (?:nay|day|do)|"
        r"(?:dang xem|dang an vao) (?:gi|co vat)?|day la (?:bia|vat|co vat))\b",
        normalized(question),
    ))
    unmapped_marker = (
        selected_marker and artifact is None and not verified_non_artifact and marker_reference
    )
    destination = question_outside_area(question, area)
    artifact_destinations = (
        referenced_tour_artifacts(area.id, question, exclude_id=artifact.id)
        if artifact else []
    )
    artifact_destination = artifact_destinations[0] if len(artifact_destinations) == 1 else None
    social = is_social_turn(question)

    def response(text, kind, sources=(), questions=(), graph_context=None, evidence=()):
        snapshot = reply_context.model_copy(update={
            "story_id": reply_context.story_id if kind == "answered" else None,
        }).model_dump() if reply_context else None
        related = [] if unmapped_marker else related_follow_ups(
            list(questions), question, graph_context=graph_context,
            evidence=evidence, area_title=area.title,
        )
        focus_names = (artifact.title, *artifact.aliases) if artifact else ()
        return {
            "answer": text, "answer_type": kind, "sources": list(sources),
            "active_area_id": area.id,
            "reply_context": snapshot,
            "follow_up_questions": follow_up_questions(
                related, area, fallback=not unmapped_marker, focus_names=focus_names,
                fallback_questions=artifact.questions() if artifact else None,
            ),
            "resolution_status": "not_found" if kind == "insufficient_evidence" else "resolved",
        }

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

    evidence = []
    graph_context = []
    if not social and destination is None and not artifact_destinations and not unmapped_marker:
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
        if artifact:
            search_question += f"\nCổ vật đang chọn: {artifact.title}"
        elif ((scene_reference or (reply_context and reply_context.story_id))
              and isinstance(scene_title, str) and scene_title.strip() and allowed_output(scene_title)):
            search_question += f"\nCảnh đang xem: {scene_title[:200]}"
            if reply_context and reply_context.highlight_title:
                search_question += f"\nĐiểm được chọn: {reply_context.highlight_title}"
        try:
            search_options = {"active_area_id": area.id}
            if artifact and artifact.artifact_key:
                search_options["artifact_key"] = artifact.artifact_key
            result = await repository.search_evidence(search_question, **search_options)
        except Exception as error:
            # Never replace unavailable area evidence with unscoped/model-memory facts.
            raise TourChatError(503, "Kho dữ liệu của khu vực đang tham quan hiện không khả dụng.") from error
        evidence = [
            item for item in result.evidence
            if getattr(item, "active_area_id", None) == area.id
            and (not artifact or not artifact.source_ids or str(item.id) in artifact.source_ids)
        ]
        graph_context = result.graph_context

    # Bound whole evidence chunks; never accidentally send unbounded adapter output.
    selected = []
    context = ""
    for item in evidence:
        block = f"[Passage {item.id}]\n{item.text}"
        if len(context) + len(block) + 2 <= 4800:
            selected.append(item)
            context += ("\n\n" if context else "") + block
    evidence = selected
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

    def infer():
        raw = generate(
            question=question, context=context, conversation=True,
            retrieval_status="available" if evidence else "not_found",
            active_area_id=area.id, user_history=user_history,
            artifact_title=artifact.title if artifact else None,
        )
        return raw, generation_details()

    try:
        raw, details = await asyncio.to_thread(infer)
        if details.truncated is True:
            raise ValueError("Truncated answer")
        answer = ConversationAnswer.model_validate_json(raw)
    except Exception:
        return response(scoped_missing(area), "insufficient_evidence")

    if social:
        if answer.answer_type == "conversation" and allowed_tour_output(answer.answer, "conversation", area):
            return response(answer.answer, "conversation", questions=answer.follow_up_questions)
        return response(
            f"Mình là trợ lý AI HeritageGraph, đồng hành cùng bạn tại {area.title}. "
            "Bạn muốn tìm hiểu điều gì trong khu vực đang tham quan?",
            "conversation",
        )

    if destination is not None:
        if (answer.answer_type == "out_of_scope"
                and allowed_tour_output(answer.answer, "out_of_scope", area, destination=destination)):
            return response(answer.answer, "out_of_scope", questions=answer.follow_up_questions)
        return response(scoped_refusal(area, destination), "out_of_scope")
    if artifact_destinations:
        route = (
            f"Bạn có thể chọn điểm {artifact_destination.title} để tìm hiểu riêng."
            if artifact_destination else
            "Có nhiều điểm trùng tên; bạn hãy chọn đúng marker để mình xác định cổ vật."
        )
        return response(
            f"Mình đang tập trung vào {artifact.title}. {route} "
            "Mình sẽ không đoán dữ kiện về điểm khác.",
            "out_of_scope",
        )

    if unmapped_marker:
        return response(
            f"Điểm đang chọn tại {area.title} chưa có ánh xạ tư liệu được xác minh, "
            "nên mình chưa thể trả lời chi tiết về điểm này.",
            "insufficient_evidence",
        )

    if story_evidence_missing:
        return response(scoped_missing(area), "insufficient_evidence")

    if answer.answer_type == "answered":
        cited = grounded_source_ids(answer.source_ids, ids)
        if not cited or (story and not set(story.source_ids) <= set(cited)):
            return response(scoped_missing(area), "insufficient_evidence")
        if not allowed_tour_output(answer.answer, "answered", area):
            return response(scoped_refusal(area), "out_of_scope")
        sources = [item.to_source() for item in evidence if str(item.id) in cited]
        return response(
            answer.answer, "answered", sources, questions=answer.follow_up_questions,
            graph_context=accepted_graph, evidence=evidence,
        )

    if answer.answer_type == "insufficient_evidence":
        return response(scoped_missing(area), "insufficient_evidence")
    if answer.answer_type == "conversation":
        return response(scoped_refusal(area), "out_of_scope")
    if not allowed_tour_output(answer.answer, "out_of_scope", area):
        return response(scoped_refusal(area), "out_of_scope")
    return response(answer.answer, "out_of_scope", questions=answer.follow_up_questions)
