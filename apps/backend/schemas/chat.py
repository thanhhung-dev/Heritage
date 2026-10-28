"""Public contracts for persisted chat; identity always comes from authentication."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, JsonValue, field_validator

MAX_CONTEXT_MESSAGES = 6
MAX_CONTEXT_MESSAGE_CHARS = 2000
MAX_CONTEXT_CHARS = 6000


class ChatContextMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_CONTEXT_MESSAGE_CHARS)


class ChatContextFields(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)

    heritage_context: str | dict[str, JsonValue] | None = None
    scene_context: str | dict[str, JsonValue] | None = None
    conversation_context: list[ChatContextMessage] = Field(default_factory=list, max_length=MAX_CONTEXT_MESSAGES)

    @field_validator("conversation_context")
    @classmethod
    def bound_conversation(cls, value: list[ChatContextMessage]):
        if sum(len(message.content) for message in value) > MAX_CONTEXT_CHARS:
            raise ValueError(f"Ngữ cảnh hội thoại không được vượt quá {MAX_CONTEXT_CHARS} ký tự.")
        return value

    @field_validator("heritage_context", "scene_context")
    @classmethod
    def bound_context(cls, value: str | dict[str, JsonValue] | None):
        serialized = json.dumps(value, ensure_ascii=False, allow_nan=False) if isinstance(value, dict) else value
        if serialized is not None and len(serialized) > 2000:
            raise ValueError("Bối cảnh không được vượt quá 2000 ký tự.")
        return value


class ChatMessageCreate(ChatContextFields):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: UUID | None = None
    heritage_id: int | None = Field(default=None, gt=0, le=2**63 - 1)


class LegacyChatRequest(ChatContextFields):
    # Keep the legacy route's explicit HTTP 400 for blank questions.
    message: str = Field(max_length=8000)
    use_rag: bool = True
    session_id: str | None = Field(default=None, max_length=128)


class ChatOutcome(BaseModel):
    """Outcome fields shared by live replies and restored assistant messages."""

    model_config = ConfigDict(from_attributes=True)

    corrected_from: str = ""
    corrected_to: str = ""
    needs_user_choice: bool = False
    suggestions: list[dict[str, JsonValue]] = Field(default_factory=list)
    entity_id: str | None = None
    intent: str | None = None
    resolution_status: str | None = None
    answer_type: str | None = None
    abstained: bool = False
    abstention_reason: Literal["insufficient_evidence", "service_unavailable"] | None = None

    def outcome_data(self) -> dict:
        return self.model_dump(include=set(ChatOutcome.model_fields))


class ChatAnswer(ChatOutcome):
    answer: str
    sources: list[dict] = Field(default_factory=list)


class LegacyChatResponse(ChatAnswer):
    """Compatibility response for POST /api/chat (HTTP 200)."""


class MessageCitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message_id: UUID
    source_title: str
    source_url: str | None = None
    relevance_score: float | None = Field(default=None, allow_inf_nan=False)


class ChatMessageResponse(ChatOutcome):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    citations: list[MessageCitationResponse] = Field(
        default_factory=list, validation_alias=AliasChoices("citation_records", "citations")
    )


class ChatResponse(ChatOutcome):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    message_id: UUID
    answer: str
    citations: list[MessageCitationResponse] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: int | None
    title: str
    heritage_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: list[ChatMessageResponse] = Field(default_factory=list)
