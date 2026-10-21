"""Unauthenticated local-only R2 knowledge administration. Never expose publicly."""
from __future__ import annotations

import asyncio
import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from apps.backend.core.config import cors_origins
from apps.backend.core.r2 import R2Storage
from apps.backend.core.search import PassageStore, SearchError
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.schemas.knowledge import DocumentPatch, DocumentRegister, FolderCreate, FolderRename, UploadCreate
from apps.backend.services.knowledge import KnowledgeService, document_out


def local_only(request: Request):
    if os.environ.get('APP_ENVIRONMENT', 'local') not in {'local', 'test'}:
        raise HTTPException(403, 'API chưa có auth, chỉ được dùng trong môi trường local/test.')
    if (not request.client or request.client.host not in {'127.0.0.1', '::1'}
            or request.url.hostname not in {'localhost', '127.0.0.1', '::1'}):
        raise HTTPException(403, 'API quản trị chưa có auth, chỉ nhận kết nối loopback.')
    origin = request.headers.get('origin')
    if origin and origin not in [*cors_origins(), str(request.base_url).rstrip('/')]:
        raise HTTPException(403, 'Origin không được phép gọi API quản trị local.')


router = APIRouter(prefix='/admin', tags=['Admin knowledge (LOCAL ONLY, no auth)'],
                   dependencies=[Depends(local_only)])


def get_storage():
    return R2Storage()


async def get_db():
    if AsyncSessionLocal.kw.get('bind') is None:
        raise HTTPException(503, 'Cần DATABASE_URL và tạo bảng knowledge để quản lý tài liệu/upload.')
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise HTTPException(503, 'Database knowledge không sẵn sàng; kiểm tra cấu hình/schema.') from None


def get_service(db=Depends(get_db), storage=Depends(get_storage)):
    return KnowledgeService(db, storage)


@router.get('/storage/entries')
def entries(prefix: str | None = Query(None, max_length=1024),
            cursor: str | None = Query(None, max_length=4096),
            limit: int = Query(100, ge=1, le=1000), storage=Depends(get_storage)):
    return storage.entries(prefix, limit, cursor)


@router.post('/storage/folders', status_code=201)
def create_folder(data: FolderCreate, storage=Depends(get_storage)):
    return storage.create_folder(data.parent_prefix, data.name)


@router.patch('/storage/folders')
def rename_folder(data: FolderRename, storage=Depends(get_storage)):
    return storage.rename_folder(data.prefix, data.name)


@router.delete('/storage/folders', status_code=204)
def delete_folder(prefix: str = Query(max_length=1024), storage=Depends(get_storage)):
    storage.delete_folder(prefix)
    return Response(status_code=204)


@router.get('/documents')
async def documents(status: Literal['uploaded', 'indexed', 'failed', 'processing'] | None = None,
                    cursor: UUID | None = None, limit: int = Query(50, ge=1, le=200),
                    service=Depends(get_service)):
    return await service.documents(status, cursor, limit)


@router.get('/documents/{document_id}')
async def document(document_id: UUID, service=Depends(get_service)):
    return document_out(await service.document(document_id))


@router.post('/documents', status_code=201)
async def register_document(data: DocumentRegister, service=Depends(get_service)):
    return await service.register(data)


@router.patch('/documents/{document_id}')
async def patch_document(document_id: UUID, data: DocumentPatch, service=Depends(get_service)):
    return await service.patch(document_id, data)


@router.delete('/documents/{document_id}', status_code=204)
async def delete_document(document_id: UUID, service=Depends(get_service)):
    await service.delete(document_id)
    return Response(status_code=204)


@router.get('/documents/{document_id}/download-url')
async def download(document_id: UUID, service=Depends(get_service)):
    doc = await service.document(document_id)
    url = await asyncio.to_thread(service.storage.presign, 'get_object', doc.object_key,
                                  filename=doc.filename)
    return {'url': url, 'expires_in': 600}


@router.get('/documents/{document_id}/chunks')
async def chunks(document_id: UUID, cursor: str | None = Query(None, max_length=512),
                 limit: int = Query(50, ge=1, le=200), service=Depends(get_service)):
    doc = await service.document(document_id)
    if doc.status != 'indexed':
        return {'items': [], 'next_cursor': None, 'status': doc.status}
    try:
        async with PassageStore() as store:
            return await store.document_chunks(doc.object_key, doc.bucket, limit=limit, after=cursor)
    except SearchError:
        raise HTTPException(503, 'Không đọc được chunk từ OpenSearch.') from None


@router.post('/uploads', status_code=201)
async def create_upload(data: UploadCreate, service=Depends(get_service)):
    return await service.create_upload(data)


@router.post('/uploads/{upload_id}/complete')
async def complete_upload(upload_id: UUID, service=Depends(get_service)):
    return await service.complete(upload_id)
