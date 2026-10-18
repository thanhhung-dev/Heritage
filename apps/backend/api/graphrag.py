"""Explicit global-search endpoint; /api/chat keeps hybrid + BGE unchanged."""
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from apps.backend.core.observability import correlation_id, rag_observation
from apps.backend.services.graphrag import run_global_query

router = APIRouter()
log = logging.getLogger(__name__)


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


@router.post('/graphrag/query', response_model=GlobalResponse)
async def query(req: GlobalQuery):
    with rag_observation('graphrag.request', input={'question': req.message}, metadata={
        'correlation_id': correlation_id.get(), 'grounding_verified': False,
    }) as observation:
        try:
            response = GlobalResponse.model_validate(await run_global_query(req.message, req.community_level))
        except Exception as error:
            log.warning('graphrag_query_unavailable error_type=%s', type(error).__name__)
            raise HTTPException(status_code=503, detail=(
                'Microsoft GraphRAG chưa sẵn sàng hoặc truy vấn thất bại; '
                'kiểm tra cấu hình/snapshot hoặc dùng /api/chat.'
            )) from None
        observation.update(output=response.model_dump())
        return response
