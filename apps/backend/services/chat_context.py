"""Bounded prompt context; UI/history text never becomes source evidence."""
import json

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
