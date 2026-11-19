"""Durable queue consumer for the existing R2 -> chunker -> BGE-M3 -> OpenSearch flow.

No process is launched by an HTTP request. Run the explicit CLI in a worker
service. A crashed RUNNING job remains locked for operator investigation.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import AsyncExitStack
from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import sys

from dotenv import load_dotenv
from sqlalchemy import select, update

from apps.backend.core.corpus import chunk_text_spans
from apps.backend.core.document_text import extract_text
from apps.backend.core.embedding import embed_texts
from apps.backend.core.r2 import R2Storage, knowledge_prefix, safe_name
from apps.backend.core.search import PassageStore
from apps.backend.db.base import AsyncSessionLocal, configure_database, dispose_database
from apps.backend.db.import_passages import import_passages
from apps.backend.models.knowledge import KnowledgeDocument
from apps.backend.models.rag_pipeline import ReindexJob, now
from apps.backend.schemas.rag_pipeline import PipelineCreate
from apps.backend.services.account_access import account_by, is_available, require_admin_role


def read_document(storage, document):
    """Bound memory and use an ETag precondition; never fetch user-supplied URLs."""
    maximum = 16 * 1024 * 1024
    if not 0 < document.size_bytes <= maximum:
        raise ValueError("Document exceeds the reindex byte limit")
    response = storage.call("get_object", Key=document.object_key, IfMatch=document.etag)
    stream = response["Body"]
    try:
        if response.get("ContentLength", 0) > maximum:
            raise ValueError("Document exceeds the reindex byte limit")
        data = stream.read(maximum + 1)
    finally:
        stream.close()
    if len(data) > maximum or len(data) != document.size_bytes:
        raise ValueError("Document content changed; register its new revision first")
    kind = PurePosixPath(document.filename).suffix.lower().lstrip(".")
    if kind not in {"txt", "md", "html", "pdf"}:
        raise ValueError("Unsupported document format")
    return extract_text(data, kind)


async def run_next(factory=AsyncSessionLocal, *, storage=None, store=None, embedder=embed_texts) -> bool:
    """Atomically claim at most one job. Dependency failures persist FAILED state."""
    async with factory() as db:
        job_id = await db.scalar(select(ReindexJob.id).where(
            ReindexJob.status == "PENDING").order_by(ReindexJob.created_at, ReindexJob.id).limit(1))
        if job_id is None:
            return False
        claimed = await db.scalar(update(ReindexJob).where(
            ReindexJob.id == job_id, ReindexJob.status == "PENDING",
        ).values(status="RUNNING", started_at=now()).returning(ReindexJob.id))
        await db.commit()
        if claimed is None:
            return False
    try:
        async with AsyncExitStack() as resources, factory() as db:
            job = await db.get(ReindexJob, job_id)
            actor = await account_by(db, account_id=int(job.requested_by))
            if not is_available(actor):
                raise ValueError("Requesting account is no longer available")
            require_admin_role(actor)
            config = PipelineCreate.model_validate({key: job.config_snapshot[key]
                for key in ("name", "chunking", "embedding", "retrieval")})
            storage = storage if storage is not None else R2Storage()
            store = store if store is not None else await resources.enter_async_context(PassageStore())
            for document_id in job.document_ids:
                # Existing knowledge mutations lock this same row. Keep it locked
                # until external writes and the per-document checkpoint finish.
                doc = (await db.scalars(select(KnowledgeDocument).where(
                    KnowledgeDocument.id == document_id).with_for_update())).one_or_none()
                snapshot = job.document_revisions[document_id]
                if (doc is None or doc.status not in {"uploaded", "indexed"}
                        or doc.bucket != storage.bucket or any(getattr(doc, key) != value
                            for key, value in snapshot.items())):
                    raise ValueError("Document scope or revision changed after scheduling")
                parent, _, name = doc.object_key.rpartition("/")
                knowledge_prefix(parent + "/")
                safe_name(name)
                text = await asyncio.to_thread(read_document, storage, doc)
                chunks = chunk_text_spans(text, **config.chunking.model_dump())
                rows = []
                for index, chunk in enumerate(chunks):
                    identity = f"{doc.bucket}:{doc.object_key}:{chunk['char_start']}:{chunk['text']}"
                    rows.append({"id": sha256(identity.encode()).hexdigest(), "text": chunk["text"],
                                 "passage_index": index, "document_key": doc.id,
                                 "object_key": doc.object_key, "bucket": doc.bucket,
                                 "location_note": doc.title, "source_url": doc.source_url or ""})
                count = await import_passages(rows, store=store, embedder=embedder)
                await store.prune_source(doc.object_key, doc.bucket, [row["id"] for row in rows])
                doc.status = "indexed"
                job.processed_documents += 1
                job.indexed_passages += count
                await db.commit()
            job.status, job.active_slot, job.finished_at = "COMPLETED", None, now()
            await db.commit()
    except (Exception, asyncio.CancelledError) as error:
        # Never expose URLs, credentials, SQL or dependency response bodies.
        async with factory() as db:
            await db.execute(update(ReindexJob).where(ReindexJob.id == job_id).values(
                status="FAILED", active_slot=None, finished_at=now(),
                error=f"Reindex failed ({type(error).__name__}); check worker dependencies and source revision.",
            ))
            await db.commit()
        if isinstance(error, asyncio.CancelledError):
            raise
    return True


async def serve(once: bool, poll_seconds: float):
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith(("postgresql+psycopg://", "postgresql+asyncpg://")):
        raise RuntimeError("Worker requires a configured asynchronous PostgreSQL DATABASE_URL")
    configure_database(database_url)
    try:
        while True:
            found = await run_next()
            if once:
                return
            if not found:
                await asyncio.sleep(poll_seconds)
    finally:
        await dispose_database()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Consume at most one pending job and exit")
    parser.add_argument("--poll-seconds", type=float, default=5)
    args = parser.parse_args()
    if not 0.1 <= args.poll_seconds <= 60:
        parser.error("--poll-seconds must be between 0.1 and 60")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(serve(args.once, args.poll_seconds))


if __name__ == "__main__":
    main()
