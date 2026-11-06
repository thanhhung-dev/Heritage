"""Grounded chat request and response contracts."""
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from apps.backend.services.tour_scope import resolve_area


class ContextMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(max_length=8000)
    use_rag: bool = True
    session_id: str | None = None
    active_area_id: str | None = Field(default=None, min_length=1, max_length=80, description=(
        "Khóa hướng dẫn viên theo khu vực đã đăng ký, ví dụ khiem-lang. "
        "Bắt buộc khi gửi ngữ cảnh tour; alias được chuẩn hóa, không fallback sang dữ liệu toàn cục."
    ))
    heritage_id: int | None = Field(default=None, gt=0)
    heritage_context: str | dict[str, JsonValue] | None = None
    scene_context: str | dict[str, JsonValue] | None = None
    conversation_context: list[ContextMessage] = Field(default_factory=list, max_length=6)

    @field_validator("active_area_id")
    @classmethod
    def canonical_area(cls, value):
        return resolve_area(value).id if value is not None else None

    @field_validator("heritage_context", "scene_context")
    @classmethod
    def bounded_context(cls, value):
        if value is not None and len(json.dumps(value, ensure_ascii=False)) > 2000:
            raise ValueError("Bối cảnh không được vượt quá 2000 ký tự.")
        return value

    @model_validator(mode="after")
    def validate_scope(self):
        if sum(len(message.content) for message in self.conversation_context) > 6000:
            raise ValueError("Ngữ cảnh hội thoại không được vượt quá 6000 ký tự.")
        has_tour_context = any(value is not None for value in (
            self.heritage_id,
        )) or isinstance(self.heritage_context, dict) or isinstance(self.scene_context, dict)
        if has_tour_context and not self.active_area_id:
            raise ValueError("Chat trong tour phải có active_area_id.")
        if self.active_area_id and isinstance(self.heritage_context, dict) and self.heritage_context:
            slug = self.heritage_context.get("slug")
            if not isinstance(slug, str) or resolve_area(slug).id != self.active_area_id:
                raise ValueError("Khu vực không khớp với di sản đang tham quan.")
        return self


class ChatMessageCreate(ChatRequest):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: UUID | None = None


class ChatOutcome(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    active_area_id: str | None = None
    follow_up_questions: list[str] = Field(default_factory=list, max_length=3, description=(
        "Câu hỏi gợi ý đã kiểm tra phạm vi active_area_id, tách biệt suggestions dùng để disambiguation."
    ))
    corrected_from: str = ""
    corrected_to: str = ""
    needs_user_choice: bool = False
    clarification_question: str | None = None
    suggestions: list[dict] = Field(default_factory=list)
    entity_id: str | None = None
    intent: str | None = None
    resolution_status: str | None = None
    answer_type: str | None = Field(default=None, description=(
        "answered, conversation, insufficient_evidence, out_of_scope hoặc suggestion. "
        "Chỉ answered có sources; conversation không yêu cầu bằng chứng lịch sử."
    ))
    abstained: bool = False
    abstention_reason: Literal["insufficient_evidence", "out_of_scope", "service_unavailable"] | None = None

    @model_validator(mode="after")
    def normalize_outcome(self):
        if self.answer_type in {"insufficient_evidence", "out_of_scope"}:
            self.abstained = True
            self.abstention_reason = self.answer_type
        if self.needs_user_choice and not self.clarification_question:
            self.clarification_question = getattr(self, "answer", None) or getattr(self, "content", None)
        return self

    def outcome_data(self) -> dict:
        return self.model_dump(include=set(ChatOutcome.model_fields))


class ChatResponse(ChatOutcome):
    answer: str
    sources: list[dict] = Field(default_factory=list)


class MessageCitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    message_id: UUID
    source_title: str
    source_url: str | None = None
    relevance_score: float | None = Field(default=None, allow_inf_nan=False)


class PersistedChatResponse(ChatResponse):
    conversation_id: UUID
    message_id: UUID
    citations: list[MessageCitationResponse] = Field(default_factory=list)


class ChatMessageResponse(ChatOutcome):
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    sources: list[dict] = Field(default_factory=list)
    citations: list[MessageCitationResponse] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: int | None
    title: str
    heritage_id: int | None = None
    active_area_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    total_messages: int = 0
