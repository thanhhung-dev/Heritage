"""Private R2 file library. Uploading does not index data in the chatbot."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from starlette.concurrency import run_in_threadpool

from apps.backend.api.knowledge_dependencies import (
    library_admin, library_db, library_storage, private_response,
)
from apps.backend.schemas.knowledge_library import (
    CompleteOut, DownloadOut, FolderOut, FolderRequest, KeyRequest, ListingOut,
    ObjectOut, PreviewOut, UploadOut, UploadRequest,
)
from apps.backend.services.knowledge_library import KnowledgeLibrary
from apps.backend.services.knowledge_policy import root_prefix

router = APIRouter(prefix="/admin/knowledge", tags=["Admin knowledge library"],
    dependencies=[Depends(library_admin), Depends(private_response)], responses={
        401: {"description": "Missing, invalid or expired authentication"},
        403: {"description": "Current administrator permission or upload ownership required"},
        404: {"description": "Object or upload session not found"},
        409: {"description": "Object or active upload conflicts; refresh before retrying"},
        422: {"description": "Invalid key, prefix, file type, size or uploaded content"},
        503: {"description": "Storage, database or secure configuration unavailable"},
    })

Key = Annotated[str, Query(min_length=1, max_length=1024)]


@router.get("/objects", response_model=ListingOut)
async def objects(prefix: Annotated[str | None, Query(max_length=1024)] = None,
                  continuationToken: Annotated[str | None, Query(min_length=1, max_length=4096)] = None,
                  limit: Annotated[int, Query(ge=1, le=1000)] = 100, storage=Depends(library_storage)):
    return await run_in_threadpool(storage.list_objects, root_prefix() if prefix is None else prefix,
                                  limit, continuationToken)


@router.post("/upload-url", response_model=UploadOut, status_code=201)
async def upload_url(data: UploadRequest, actor=Depends(library_admin),
                     db=Depends(library_db), storage=Depends(library_storage)):
    return await KnowledgeLibrary(db, storage).begin_upload(data, actor)


@router.post("/uploads/{uploadId}/complete", response_model=CompleteOut,
             responses={410: {"description": "Upload session expired"}})
async def complete(uploadId: UUID, actor=Depends(library_admin),
                   db=Depends(library_db), storage=Depends(library_storage)):
    return await KnowledgeLibrary(db, storage).complete(uploadId, actor)


@router.get("/object", response_model=ObjectOut)
async def object_info(key: Key, storage=Depends(library_storage)):
    return await run_in_threadpool(storage.object_info, key)


@router.post("/download-url", response_model=DownloadOut)
async def download_url(data: KeyRequest, storage=Depends(library_storage)):
    return await run_in_threadpool(storage.download, data.key)


@router.get("/preview", response_model=PreviewOut, responses={
    413: {"description": "File exceeds configured preview size"},
    415: {"description": "Only .md, .txt and .json support preview"},
})
async def preview(key: Key, storage=Depends(library_storage)):
    return await run_in_threadpool(storage.preview, key)


@router.post("/folders", response_model=FolderOut, status_code=201)
async def folder(data: FolderRequest, storage=Depends(library_storage)):
    return await run_in_threadpool(storage.create_folder, data.parentPrefix, data.folderName)


@router.delete("/objects", status_code=204)
async def delete_object(data: KeyRequest, storage=Depends(library_storage)):
    await run_in_threadpool(storage.delete_file, data.key)
    return Response(status_code=204, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
