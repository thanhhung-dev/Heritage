"""Bounded prompt context; UI/history text never becomes source evidence."""
import json
import re

from apps.backend.core.textutil import strip_accents

from apps.backend.schemas.chat import (
    ChatContextMessage, ChatMessageCreate, LegacyChatRequest,
    MAX_CONTEXT_CHARS, MAX_CONTEXT_MESSAGES, MAX_CONTEXT_MESSAGE_CHARS,
)


def question_with_context(request: ChatMessageCreate | LegacyChatRequest) -> str:
    parts = [request.message]
    for label, value in (("Di sản đang xem", request.heritage_context), ("Cảnh đang xem", request.scene_context)):
        if value:
            text = json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value
            parts.append(f"{label} (bối cảnh do người dùng cung cấp): {text}")
    return "\n\n".join(parts)


def retrieval_question(question: str, history: list[ChatContextMessage]) -> str:
    # Qualify follow-up retrieval with the latest user question, never a previous
    # assistant answer. Retrieved passages still supply every factual citation.
    previous = next((message.content for message in reversed(history) if message.role == "user"), None)
    current = strip_accents(question.split("\n\n", 1)[0]).lower()
    followup = re.search(
        r"\b(no|nay|do|o day|noi day|con kien truc|con lich su|con ve|biet them|noi them|tiep tuc)\b", current,
    ) or re.search(r"^(o dau|xay (?:dung )?(?:khi nao|nam nao)|nam nao|ai xay|kien truc (?:the nao|ra sao))\b", current)
    if not previous or not followup:
        return question
    return f"Câu hỏi trước (ngữ cảnh, không phải bằng chứng): {previous[:1000]}\n\nCâu hỏi hiện tại: {question}"


def bounded_history(rows) -> list[ChatContextMessage]:
    # Rows arrive newest first from an already ownership-scoped, limited query.
    history = [ChatContextMessage(role=row.role, content=row.content[:MAX_CONTEXT_MESSAGE_CHARS])
               for row in reversed(rows) if row.content.strip()]
    history = history[-MAX_CONTEXT_MESSAGES:]
    size = sum(len(message.content) for message in history)
    while history and size > MAX_CONTEXT_CHARS:
        size -= len(history.pop(0).content)
    while history and history[0].role == "assistant":
        history.pop(0)
    return history
