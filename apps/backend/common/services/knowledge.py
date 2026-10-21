"""Durable document/upload lifecycle; R2 I/O never blocks the async event loop."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.common.storage.r2 import FILE_TYPES, R2Storage, knowledge_prefix, safe_name
from apps.backend.common.search.opensearch import PassageStore, SearchError
from apps.backend.common.models.knowledge import KnowledgeDocument, KnowledgeUpload


def document_out(doc):
    return {column.name: getattr(doc, column.name) for column in doc.__table__.columns}


class KnowledgeService:
    def __init__(self, session: AsyncSession, storage: R2Storage):
        self.session, self.storage = session, storage

    async def document(self, document_id, *, lock=False):
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == str(document_id))
        if lock:
            stmt = stmt.with_for_update()
        doc = (await self.session.execute(stmt)).scalar_one_or_none()
        if doc is None or doc.status == 'deleted':
            raise HTTPException(404, 'Không tìm thấy tài liệu.')
        if doc.bucket != self.storage.bucket:
            raise HTTPException(409, 'Tài liệu thuộc bucket khác cấu hình hiện tại.')
        knowledge_prefix(doc.object_key.rsplit('/', 1)[0] + '/')
        return doc

    async def documents(self, status, cursor, limit):
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.bucket == self.storage.bucket,
            KnowledgeDocument.status != 'deleted',
            KnowledgeDocument.object_key.startswith(knowledge_prefix(), autoescape=True),
        )
        if status:
            stmt = stmt.where(KnowledgeDocument.status == status)
        if cursor:
            stmt = stmt.where(KnowledgeDocument.id > str(cursor))
        rows = list((await self.session.scalars(stmt.order_by(KnowledgeDocument.id).limit(limit + 1))).all())
        return {'items': [document_out(d) for d in rows[:limit]],
                'next_cursor': rows[limit - 1].id if len(rows) > limit else None}

    async def register(self, data):
        parent, _, filename = data.object_key.rpartition('/')
        knowledge_prefix(parent + '/')
        safe_name(filename)
        content_type = FILE_TYPES.get(PurePosixPath(filename).suffix.lower())
        if not content_type:
            raise HTTPException(422, 'Chỉ đăng ký file TXT/MD/HTML/PDF.')
        head = await asyncio.to_thread(self.storage.call, 'head_object', Key=data.object_key)
        if not 0 < head['ContentLength'] <= int(os.environ.get('R2_UPLOAD_MAX_BYTES', str(25 * 1024 * 1024))):
            raise HTTPException(422, 'File rỗng hoặc vượt giới hạn dung lượng.')
        head = await asyncio.to_thread(self.storage.verify_upload, data.object_key, filename,
                                      head['ContentLength'], content_type)
        doc = KnowledgeDocument(
            title=data.title or filename, region=data.region, source_type=data.source_type,
            source_url=data.source_url, bucket=self.storage.bucket, object_key=data.object_key,
            filename=filename, content_type=content_type, size_bytes=head['ContentLength'], etag=head['ETag'],
            status='indexed' if await self.source_in_use(data.object_key) else 'uploaded',
        )
        self.session.add(doc)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(409, 'Object đã được đăng ký trong kho tài liệu.') from None
        return document_out(doc)

    async def source_in_use(self, key):
        try:
            async with PassageStore() as store:
                return await store.source_in_use(key, self.storage.bucket)
        except SearchError:
            raise HTTPException(503, 'Cần OpenSearch sẵn sàng để kiểm tra tham chiếu trước thao tác này.') from None

    async def create_upload(self, data):
        parent = knowledge_prefix(data.parent_prefix)
        filename = safe_name(data.filename)
        content_type = FILE_TYPES.get(PurePosixPath(filename).suffix.lower())
        if not content_type or data.content_type != content_type:
            raise HTTPException(422, 'Chỉ hỗ trợ TXT/MD/HTML/PDF với content type đúng định dạng.')
        if data.size_bytes > int(os.environ.get('R2_UPLOAD_MAX_BYTES', str(25 * 1024 * 1024))):
            raise HTTPException(422, 'File vượt giới hạn dung lượng upload.')
        doc = await self.document(data.document_id, lock=True) if data.document_id else None
        if doc and doc.status not in {'uploaded', 'indexed', 'failed'}:
            raise HTTPException(409, 'Không thay file khi tài liệu đang được xử lý.')
        uid = str(uuid4())
        upload = KnowledgeUpload(
            id=uid, document_id=doc.id if doc else None, base_revision=doc.revision if doc else None,
            bucket=self.storage.bucket, parent_prefix=parent,
            staging_key=f'_admin_uploads/{uid}/{filename}', final_key=f'{parent}{uid}-{filename}',
            filename=filename, content_type=content_type, size_bytes=data.size_bytes,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        url = await asyncio.to_thread(self.storage.presign, 'put_object', upload.staging_key,
                                      content_type=content_type)
        self.session.add(upload)
        await self.session.commit()
        return {'upload_id': uid, 'method': 'PUT', 'upload_url': url,
                'headers': {'Content-Type': content_type}, 'expires_at': upload.expires_at}

    async def complete(self, upload_id):
        upload = (await self.session.execute(select(KnowledgeUpload).where(
            KnowledgeUpload.id == str(upload_id)).with_for_update())).scalar_one_or_none()
        if upload is None:
            raise HTTPException(404, 'Không tìm thấy phiên upload.')
        if upload.bucket != self.storage.bucket:
            raise HTTPException(409, 'Phiên upload thuộc bucket khác.')
        knowledge_prefix(upload.parent_prefix)
        if upload.completed_at:
            doc = await self.session.get(KnowledgeDocument, upload.document_id)
            if doc is None or doc.status == 'deleted':
                raise HTTPException(409, 'Tài liệu của phiên upload đã bị xóa.')
            return document_out(doc)
        expires_at = upload.expires_at
        if expires_at.tzinfo is None:  # SQLite tests return naive UTC datetimes.
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(409, 'Phiên upload hết hạn; tạo phiên mới.')
        doc = await self.document(upload.document_id, lock=True) if upload.document_id else None
        if doc and (doc.revision != upload.base_revision or doc.status not in {'uploaded', 'indexed', 'failed'}):
            raise HTTPException(409, 'Tài liệu đã thay đổi; tạo lại phiên upload.')
        head = await asyncio.to_thread(self.storage.verify_upload, upload.staging_key,
            upload.filename, upload.size_bytes, upload.content_type)
        await asyncio.to_thread(self.storage.finalize, upload.staging_key, upload.final_key, head['ETag'])
        if doc is None:
            doc = KnowledgeDocument(id=str(uuid4()), title=upload.filename,
                                    bucket=upload.bucket, revision=0)
            self.session.add(doc)
        doc.object_key, doc.filename = upload.final_key, upload.filename
        doc.content_type, doc.size_bytes, doc.etag = upload.content_type, upload.size_bytes, head['ETag']
        doc.revision += 1
        doc.status = 'uploaded'
        upload.document_id, upload.completed_at = doc.id, datetime.now(timezone.utc)
        await self.session.commit()
        return document_out(doc)

    async def patch(self, document_id, data):
        doc = await self.document(document_id, lock=True)
        if doc.status not in {'uploaded', 'failed'}:
            raise HTTPException(409, 'Chưa hỗ trợ sửa metadata tài liệu đã index/đang xử lý.')
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(doc, key, value)
        doc.revision += 1
        await self.session.commit()
        return document_out(doc)

    async def delete(self, document_id):
        doc = await self.document(document_id, lock=True)
        if doc.status not in {'uploaded', 'failed'} or await self.source_in_use(doc.object_key):
            raise HTTPException(409, 'Cần gỡ chunk khỏi OpenSearch trước khi xóa tài liệu đã index.')
        await asyncio.to_thread(self.storage.call, 'delete_object', Key=doc.object_key)
        doc.status = 'deleted'
        doc.revision += 1
        await self.session.commit()
