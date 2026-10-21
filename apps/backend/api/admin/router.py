"""Local-only R2 knowledge administration, restricted to ADMIN accounts."""
from fastapi import APIRouter, Depends

from apps.backend.api.admin.dependencies import local_only
from apps.backend.core.security import require_admin
from apps.backend.api.admin.documents import router as documents
from apps.backend.api.admin.storage import router as storage
from apps.backend.api.admin.uploads import router as uploads

router = APIRouter(
    prefix="/admin",
    tags=["Admin knowledge"],
    dependencies=[Depends(local_only), Depends(require_admin)],
)
router.include_router(storage.router)
router.include_router(documents.router)
router.include_router(uploads.router)
