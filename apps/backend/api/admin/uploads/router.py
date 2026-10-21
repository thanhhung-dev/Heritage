"""Presigned upload and replacement lifecycle."""
from uuid import UUID

from fastapi import APIRouter, Depends

from apps.backend.api.admin.dependencies import get_service
from apps.backend.api.admin.uploads.schemas import UploadCreate

router = APIRouter(prefix='/uploads')


@router.post('', status_code=201)
async def create_upload(data: UploadCreate, service=Depends(get_service)):
    return await service.create_upload(data)


@router.post('/{upload_id}/complete')
async def complete_upload(upload_id: UUID, service=Depends(get_service)):
    return await service.complete(upload_id)
