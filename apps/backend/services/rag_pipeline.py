"""Administrative pipeline settings and explicitly scoped reindex scheduling."""
from __future__ import annotations

import os
from pathlib import PurePosixPath

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.r2 import knowledge_prefix, safe_name
from apps.backend.models.knowledge import KnowledgeDocument
from apps.backend.models.rag_pipeline import RagPipeline, ReindexJob
from apps.backend.schemas.rag_pipeline import JobOut, PipelineCreate, PipelineOut, PipelineUpdate


class PipelineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def pipeline(self, pipeline_id: str, *, lock=False):
        stmt = select(RagPipeline).where(RagPipeline.id == pipeline_id)
        if lock:
            stmt = stmt.with_for_update()
        row = (await self.db.scalars(stmt)).one_or_none()
        if row is None:
            raise HTTPException(404, "Pipeline not found.")
        return row

    async def commit(self):
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(409, "Pipeline name already exists or a reindex job is active.") from None

    async def create(self, data: PipelineCreate):
        row = RagPipeline(**data.model_dump())
        self.db.add(row)
        await self.commit()
        return PipelineOut.model_validate(row)

    async def list(self, cursor, limit):
        stmt = select(RagPipeline).order_by(RagPipeline.id).limit(limit + 1)
        if cursor:
            stmt = stmt.where(RagPipeline.id > cursor)
        rows = list((await self.db.scalars(stmt)).all())
        return {"items": [PipelineOut.model_validate(row) for row in rows[:limit]],
                "next_cursor": rows[limit - 1].id if len(rows) > limit else None}

    async def update(self, pipeline_id: str, data: PipelineUpdate):
        await self.pipeline(pipeline_id, lock=True)
        active = await self.db.scalar(select(ReindexJob.id).where(
            ReindexJob.pipeline_id == pipeline_id, ReindexJob.active_slot == 1))
        if active:
            raise HTTPException(409, "Pipeline has an active reindex job.")
        values = data.model_dump(exclude_unset=True, exclude={"expected_revision"})
        row = (await self.db.scalars(update(RagPipeline).where(
            RagPipeline.id == pipeline_id, RagPipeline.revision == data.expected_revision,
        ).values(**values, revision=RagPipeline.revision + 1).returning(RagPipeline),
                                    execution_options={"populate_existing": True})).one_or_none()
        if row is None:
            raise HTTPException(409, "Pipeline revision changed; reload before editing.")
        await self.commit()
        return PipelineOut.model_validate(row)

    async def delete(self, pipeline_id: str):
        await self.pipeline(pipeline_id, lock=True)
        if await self.db.scalar(select(ReindexJob.id).where(ReindexJob.pipeline_id == pipeline_id).limit(1)):
            raise HTTPException(409, "Pipeline has job history and cannot be deleted.")
        await self.db.execute(delete(RagPipeline).where(RagPipeline.id == pipeline_id))
        await self.commit()

    async def trigger(self, pipeline_id: str, document_ids: list[str], actor: str):
        pipeline = await self.pipeline(pipeline_id, lock=True)
        if await self.db.scalar(select(ReindexJob.id).where(ReindexJob.active_slot == 1)):
            raise HTTPException(409, "A reindex job is already pending or running.")
        documents = list((await self.db.scalars(select(KnowledgeDocument).where(
            KnowledgeDocument.id.in_(document_ids)).with_for_update())).all())
        if len(documents) != len(document_ids):
            raise HTTPException(404, "One or more documents were not found.")
        bucket = os.environ.get("R2_BUCKET", "")
        if not bucket:
            raise HTTPException(503, "R2_BUCKET must be configured.")
        snapshots = {}
        for doc in documents:
            parent, _, name = doc.object_key.rpartition("/")
            knowledge_prefix(parent + "/")
            safe_name(name)
            if doc.status not in {"uploaded", "indexed"} or doc.bucket != bucket:
                raise HTTPException(409, "Document is unavailable or outside the configured bucket.")
            if PurePosixPath(name).suffix.lower() not in {".txt", ".md", ".html", ".pdf"}:
                raise HTTPException(422, "Unsupported document format.")
            snapshots[doc.id] = {"revision": doc.revision, "etag": doc.etag,
                                 "bucket": doc.bucket, "object_key": doc.object_key}
        row = ReindexJob(
            pipeline_id=pipeline_id, pipeline_revision=pipeline.revision,
            config_snapshot=PipelineOut.model_validate(pipeline).model_dump(mode="json"),
            document_ids=document_ids, document_revisions=snapshots, requested_by=actor,
            active_slot=1, status="PENDING",
        )
        self.db.add(row)
        await self.commit()
        return JobOut.model_validate(row)

    async def job(self, job_id: str):
        row = await self.db.get(ReindexJob, job_id)
        if row is None:
            raise HTTPException(404, "Reindex job not found.")
        return JobOut.model_validate(row)
