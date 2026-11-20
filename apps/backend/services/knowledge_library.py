"""Upload transactions only. This service never imports retrieval or RAG services."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from apps.backend.models.knowledge_library import LibraryUpload
from apps.backend.services.knowledge_policy import (
    BUCKET, SESSION_SECONDS, STAGING, root_prefix, upload_key,
)


def utcnow():
    return datetime.now(timezone.utc)


def aware(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class KnowledgeLibrary:
    def __init__(self, db, storage):
        self.db, self.storage = db, storage

    async def begin_upload(self, data, actor_id):
        key = upload_key(data.folder, data.filename, data.contentType, data.size)
        now, upload_id = utcnow(), str(uuid4())
        staging_key = root_prefix() + STAGING + upload_id + "/" + data.filename
        if len(staging_key.encode("utf-8")) > 1024:
            raise HTTPException(422, "Configured scope leaves insufficient key length for upload staging.")
        if await run_in_threadpool(self.storage.maybe_head, key) is not None:
            raise HTTPException(409, "Destination file already exists.")
        # A logical folder can exist without a marker object.
        # At the maximum key length, key + '/' cannot be a valid object/prefix.
        if len(key.encode("utf-8")) < 1024:
            page = await run_in_threadpool(self.storage.call, "list_objects_v2", Prefix=key + "/", MaxKeys=1)
            if page.get("Contents"):
                raise HTTPException(409, "A folder already uses this destination name.")
        await self.db.execute(update(LibraryUpload).where(LibraryUpload.status == "PENDING",
            LibraryUpload.expires_at <= now).values(status="EXPIRED", reservation_key=None))
        upload = LibraryUpload(id=upload_id, actor_id=actor_id, bucket=BUCKET, final_key=key,
            reservation_key=key, staging_key=staging_key,
            filename=data.filename, content_type=data.contentType, size_bytes=data.size,
            status="PENDING", expires_at=now + timedelta(seconds=SESSION_SECONDS))
        self.db.add(upload)
        try:
            await self.db.flush()
            result = await run_in_threadpool(self.storage.upload_url, upload)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(409, "Another active upload reserves this filename.") from None
        return result

    async def _finish(self, upload, head):
        upload.status, upload.reservation_key = "COMPLETED", None
        upload.completed_at = upload.completed_at or utcnow()
        upload.final_etag = head["ETag"]
        await self.db.commit()
        return {"uploadId": upload.id, "object": self.storage.metadata(upload.final_key, head)}

    async def complete(self, upload_id, actor_id):
        upload = (await self.db.scalars(select(LibraryUpload).where(LibraryUpload.id == str(upload_id))
                                       .with_for_update())).one_or_none()
        if upload is None:
            raise HTTPException(404, "Upload session not found.")
        if upload.actor_id != actor_id:
            raise HTTPException(403, "This upload session belongs to another administrator.")
        if upload.bucket != BUCKET:
            raise HTTPException(409, "Invalid knowledge upload bucket.")
        # Scope changes must not allow an older session to escape the new scope.
        from apps.backend.services.knowledge_policy import library_path
        library_path(upload.final_key)
        final = await run_in_threadpool(self.storage.maybe_head, upload.final_key)
        if final is not None:
            if final.get("Metadata", {}).get("upload-id") == upload.id:
                self.storage.verify_identity(upload, final, published=True)
                if upload.final_etag and upload.final_etag != final["ETag"]:
                    raise HTTPException(409, "Completed object has since changed.")
                # Recovery is allowed after expiry only when publication already happened.
                return await self._finish(upload, final)
            if upload.status == "PENDING":
                upload.status, upload.reservation_key = "CONFLICT", None
                await self.db.commit()
            raise HTTPException(409, "Destination exists and belongs to another write.")
        if upload.status == "COMPLETED":
            raise HTTPException(404, "Completed object no longer exists; it will not be recreated.")
        if aware(upload.expires_at) <= utcnow() or upload.status == "EXPIRED":
            upload.status, upload.reservation_key = "EXPIRED", None
            await self.db.commit()
            raise HTTPException(410, "Upload session expired; request another upload URL.")
        if upload.status != "PENDING":
            raise HTTPException(409, "Upload session cannot be completed.")
        try:
            head = await run_in_threadpool(self.storage.publish_verified, upload)
        except HTTPException as error:
            if error.status_code == 409:
                # Keep PENDING on an ambiguous conditional failure. A retry HEAD
                # can recover our committed write, or mark an external conflict.
                await self.db.rollback()
            raise
        return await self._finish(upload, head)
