"""Versioned pipeline settings matching the existing chunker and embedding model."""
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from apps.backend.ai.providers.embedding import EMBEDDING_ID


def utc_timestamp(value):
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


UtcTimestamp = Annotated[datetime, BeforeValidator(utc_timestamp)]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ChunkingConfig(StrictModel):
    max_chars: int = Field(default=2400, ge=32, le=16000, strict=True)
    overlap_chars: int = Field(default=300, ge=0, strict=True)

    @model_validator(mode="after")
    def valid_overlap(self):
        if self.overlap_chars >= self.max_chars // 2:
            raise ValueError("overlap_chars must be less than max_chars // 2")
        return self


class EmbeddingConfig(StrictModel):
    model: str = EMBEDDING_ID
    dimensions: Literal[1024] = 1024

    @model_validator(mode="after")
    def supported_model(self):
        if self.model != EMBEDDING_ID:
            raise ValueError("Only the project's pinned BGE-M3 embedding model is supported")
        return self


class RetrievalConfig(StrictModel):
    strategy: Literal["opensearch-hybrid"] = "opensearch-hybrid"
    top_k: int = Field(default=20, ge=1, le=100, strict=True)
    min_similarity: float = Field(default=0.55, ge=0, le=1, allow_inf_nan=False)


class PipelineCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120, pattern=r"^\S(?:.*\S)?$")
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)


class PipelineUpdate(StrictModel):
    expected_revision: int = Field(ge=1, strict=True)
    name: str | None = Field(default=None, min_length=1, max_length=120, pattern=r"^\S(?:.*\S)?$")
    chunking: ChunkingConfig | None = None
    embedding: EmbeddingConfig | None = None
    retrieval: RetrievalConfig | None = None

    @model_validator(mode="after")
    def nonempty(self):
        changed = self.model_fields_set - {"expected_revision"}
        if not changed or any(getattr(self, field) is None for field in changed):
            raise ValueError("Provide at least one non-null configuration field")
        return self


class PipelineOut(PipelineCreate):
    id: str
    revision: int
    created_at: UtcTimestamp
    updated_at: UtcTimestamp


class PipelineList(StrictModel):
    items: list[PipelineOut]
    next_cursor: str | None


class ReindexRequest(StrictModel):
    document_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def unique_documents(self):
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("document_ids must be unique")
        return self


class JobOut(StrictModel):
    id: str
    pipeline_id: str
    pipeline_revision: int
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    document_ids: list[str]
    processed_documents: int
    indexed_passages: int
    error: str | None
    created_at: UtcTimestamp
    started_at: UtcTimestamp | None
    finished_at: UtcTimestamp | None
