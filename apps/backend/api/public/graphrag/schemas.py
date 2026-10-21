"""Standalone GraphRAG query contracts."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GlobalQuery(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    community_level: int = Field(default=0, ge=0, le=10)

    @field_validator('message')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('message must not be blank')
        return value.strip()


class GlobalResponse(BaseModel):
    answer: str
    snapshot_id: str
    context_reports: list[dict]
    sources: list[dict]
    source_scope: Literal['community_context']
    grounding_verified: Literal[False] = False
