"""Document metadata, downloads and indexed chunks."""
import asyncio
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from apps.backend.api.admin.dependencies import get_service
from apps.backend.api.admin.documents.schemas import DocumentPatch, DocumentRegister
from apps.backend.common.search.opensearch import PassageStore, SearchError
from apps.backend.common.services.knowledge import document_out

router = APIRouter(prefix='/documents')


@router.get('')
async def documents(status: Literal['uploaded', 'indexed', 'failed', 'processing'] | None = None,
                    cursor: UUID | None = None, limit: int = Query(50, ge=1, le=200),
                    service=Depends(get_service)):
    return await service.documents(status, cursor, limit)


@router.get('/{document_id}')
async def document(document_id: UUID, service=Depends(get_service)):
    return document_out(await service.document(document_id))


@router.post('', status_code=201)
async def register_document(data: DocumentRegister, service=Depends(get_service)):
    return await service.register(data)


@router.patch('/{document_id}')
async def patch_document(document_id: UUID, data: DocumentPatch, service=Depends(get_service)):
    return await service.patch(document_id, data)


@router.delete('/{document_id}', status_code=204)
async def delete_document(document_id: UUID, service=Depends(get_service)):
    await service.delete(document_id)
    return Response(status_code=204)


@router.get('/{document_id}/download-url')
async def download(document_id: UUID, service=Depends(get_service)):
    doc = await service.document(document_id)
    url = await asyncio.to_thread(service.storage.presign, 'get_object', doc.object_key,
                                  filename=doc.filename)
    return {'url': url, 'expires_in': 600}


@router.get('/{document_id}/chunks')
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
