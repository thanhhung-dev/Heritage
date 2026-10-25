"""Public contracts for persisted chat; identity always comes from authentication."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, JsonValue, field_validator


class ChatMessageCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=8000)
    conversation_id: UUID | None = None
    heritage_id: int | None = Field(default=None, gt=0, le=2**63 - 1)
    heritage_context: str | dict[str, JsonValue] | None = None
    scene_context: str | dict[str, JsonValue] | None = None

    @field_validator("heritage_context", "scene_context")
    @classmethod
    def bound_context(cls, value: str | dict[str, JsonValue] | None):
        serialized = json.dumps(value, ensure_ascii=False, allow_nan=False) if isinstance(value, dict) else value
        if serialized is not None and len(serialized) > 2000:
            raise ValueError("Bối cảnh không được vượt quá 2000 ký tự.")
        return value


class MessageCitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message_id: UUID
    source_title: str
    source_url: str | None = None
    relevance_score: float | None = Field(default=None, allow_inf_nan=False)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    citations: list[MessageCitationResponse] = Field(
        default_factory=list, validation_alias=AliasChoices("citation_records", "citations")
    )


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    message_id: UUID
    answer: str
    citations: list[MessageCitationResponse] = Field(default_factory=list)
    resolution_status: str | None = None
    answer_type: str | None = None


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
