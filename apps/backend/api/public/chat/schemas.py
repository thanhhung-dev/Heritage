"""Grounded chat request and response contracts."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = Field(default_factory=list)
    corrected_from: str = ""
    corrected_to: str = ""
    needs_user_choice: bool = False
    suggestions: list[dict] = Field(default_factory=list)
    entity_id: str | None = None
    intent: str | None = None
    resolution_status: str | None = None
    answer_type: str | None = None
