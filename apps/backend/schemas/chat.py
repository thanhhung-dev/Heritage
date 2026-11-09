"""Compatibility exports for the shared standalone/3D/persisted chat contract."""
from apps.backend.api.public.chat.schemas import (
    ChatMessageCreate, ChatMessageResponse, ChatOutcome, ConversationDetailResponse,
    ConversationResponse, MessageCitationResponse,
    ChatRequest as LegacyChatRequest, ChatResponse as LegacyChatResponse,
    ChatResponse as ChatAnswer, ContextMessage as ChatContextMessage,
    PersistedChatResponse as ChatResponse,
)

MAX_CONTEXT_MESSAGES = 6
MAX_CONTEXT_MESSAGE_CHARS = 2000
MAX_CONTEXT_CHARS = 6000

__all__ = [
    "ChatMessageCreate", "ChatMessageResponse", "ChatOutcome", "ChatResponse", "ChatAnswer",
    "ChatContextMessage", "ConversationDetailResponse", "ConversationResponse", "MessageCitationResponse",
    "LegacyChatRequest", "LegacyChatResponse", "MAX_CONTEXT_MESSAGES", "MAX_CONTEXT_MESSAGE_CHARS", "MAX_CONTEXT_CHARS",
]
