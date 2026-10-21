"""Standalone global search; its source candidates also join hybrid /api/chat."""
import logging

from fastapi import APIRouter, HTTPException

from apps.backend.api.public.graphrag.schemas import GlobalQuery, GlobalResponse
from apps.backend.common.observability import correlation_id, rag_observation
from apps.backend.ai.retrieval.graphrag import run_global_query

router = APIRouter()
log = logging.getLogger(__name__)


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
