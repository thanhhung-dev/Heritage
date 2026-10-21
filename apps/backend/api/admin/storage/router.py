"""Browse R2 objects and manage empty folders."""
from fastapi import APIRouter, Depends, Query, Response

from apps.backend.api.admin.dependencies import get_storage
from apps.backend.api.admin.storage.schemas import FolderCreate, FolderRename

router = APIRouter(prefix='/storage')


@router.get('/entries')
def entries(prefix: str | None = Query(None, max_length=1024),
            cursor: str | None = Query(None, max_length=4096),
            limit: int = Query(100, ge=1, le=1000),
            children_limit: int = Query(100, ge=1, le=1000), storage=Depends(get_storage)):
    return storage.entries(prefix, limit, cursor, children_limit=children_limit)


@router.post('/folders', status_code=201)
def create_folder(data: FolderCreate, storage=Depends(get_storage)):
    return storage.create_folder(data.parent_prefix, data.name)


@router.patch('/folders')
def rename_folder(data: FolderRename, storage=Depends(get_storage)):
    return storage.rename_folder(data.prefix, data.name)


@router.delete('/folders', status_code=204)
def delete_folder(prefix: str = Query(max_length=1024), storage=Depends(get_storage)):
    storage.delete_folder(prefix)
    return Response(status_code=204)
