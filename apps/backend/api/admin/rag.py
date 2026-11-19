"""Admin RAG configuration and durable job APIs, separate from local file tools."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import get_auth_db, require_admin
from apps.backend.schemas.rag_pipeline import (
    JobOut, PipelineCreate, PipelineList, PipelineOut, PipelineUpdate, ReindexRequest,
)
from apps.backend.services.rag_pipeline import PipelineService

router = APIRouter(prefix="/api/admin/rag", tags=["Admin RAG"], dependencies=[Depends(require_admin)],
                   responses={401: {"description": "Invalid session"}, 403: {"description": "Admin required"},
                              404: {"description": "Record not found"}, 409: {"description": "Conflict"},
                              503: {"description": "Database or configuration unavailable"}})


def service(db: AsyncSession = Depends(get_auth_db)):
    return PipelineService(db)


@router.post("/pipelines", response_model=PipelineOut, status_code=201)
async def create_pipeline(data: PipelineCreate, svc: PipelineService = Depends(service)):
    return await svc.create(data)


@router.get("/pipelines", response_model=PipelineList)
async def list_pipelines(cursor: UUID | None = None,
                         limit: Annotated[int, Query(ge=1, le=100)] = 20,
                         svc: PipelineService = Depends(service)):
    return await svc.list(str(cursor) if cursor else None, limit)


@router.get("/pipelines/{pipeline_id}", response_model=PipelineOut)
async def get_pipeline(pipeline_id: UUID, svc: PipelineService = Depends(service)):
    return PipelineOut.model_validate(await svc.pipeline(str(pipeline_id)))


@router.patch("/pipelines/{pipeline_id}", response_model=PipelineOut)
async def update_pipeline(pipeline_id: UUID, data: PipelineUpdate, svc: PipelineService = Depends(service)):
    return await svc.update(str(pipeline_id), data)


@router.delete("/pipelines/{pipeline_id}", status_code=204)
async def delete_pipeline(pipeline_id: UUID, svc: PipelineService = Depends(service)):
    await svc.delete(str(pipeline_id))
    return Response(status_code=204)


@router.post("/pipelines/{pipeline_id}/reindex", response_model=JobOut, status_code=202)
async def trigger_reindex(pipeline_id: UUID, data: ReindexRequest,
                          user: dict = Depends(require_admin), svc: PipelineService = Depends(service)):
    return await svc.trigger(str(pipeline_id), [str(value) for value in data.document_ids], user["sub"])


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: UUID, svc: PipelineService = Depends(service)):
    return await svc.job(str(job_id))
