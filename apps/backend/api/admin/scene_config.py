"""Per-scene camera and environment configuration using the public viewer contract."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.api.admin.scenes import ResourceId
from apps.backend.core.security import get_auth_db, require_admin
from apps.backend.schemas.scene_config import SceneConfigOut, SceneConfigUpdate
from apps.backend.services.scene_config import SceneConfigService

router = APIRouter(prefix="/api/admin/scenes", tags=["Admin 3D configuration"],
                   dependencies=[Depends(require_admin)],
                   responses={401: {"description": "Invalid session"}, 403: {"description": "Admin required"},
                              404: {"description": "Scene not found"},
                              422: {"description": "Invalid camera, sky or asset reference"},
                              503: {"description": "Database unavailable"}})


def service(db: AsyncSession = Depends(get_auth_db)):
    return SceneConfigService(db)


@router.get("/{scene_id}/3d-config", response_model=SceneConfigOut)
async def get_config(scene_id: ResourceId, svc: SceneConfigService = Depends(service)):
    return await svc.get(scene_id)


@router.put("/{scene_id}/3d-config", response_model=SceneConfigOut)
async def save_config(scene_id: ResourceId, data: SceneConfigUpdate, svc: SceneConfigService = Depends(service)):
    return await svc.save(scene_id, data)
