"""Heritage-scoped administrative scene metadata and ordering."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import get_auth_db, require_admin
from apps.backend.schemas.admin_scene import SceneCreate, SceneList, SceneOrder, SceneOut, SceneUpdate
from apps.backend.services.admin_scene import SceneService

ResourceId = Annotated[int, Path(gt=0, lt=2**63)]
router = APIRouter(prefix="/api/admin/heritages/{heritage_id}/scenes", tags=["Admin scenes"],
                   dependencies=[Depends(require_admin)],
                   responses={401: {"description": "Invalid session"}, 403: {"description": "Admin required"},
                              404: {"description": "Heritage or scene not found"},
                              409: {"description": "Sequence or stale-order conflict"},
                              503: {"description": "Database unavailable"}})


def service(db: AsyncSession = Depends(get_auth_db)):
    return SceneService(db)


@router.post("", response_model=SceneOut, status_code=201)
async def create(heritage_id: ResourceId, data: SceneCreate, svc: SceneService = Depends(service)):
    return await svc.create(heritage_id, data)


@router.get("", response_model=SceneList)
async def list_scenes(heritage_id: ResourceId,
                      after_sequence: Annotated[int | None, Query(ge=-1)] = None,
                      limit: Annotated[int, Query(ge=1, le=1000)] = 100,
                      svc: SceneService = Depends(service)):
    return await svc.list(heritage_id, after_sequence, limit)


@router.patch("/order", response_model=SceneList)
async def reorder(heritage_id: ResourceId, data: SceneOrder, svc: SceneService = Depends(service)):
    return await svc.reorder(heritage_id, data)


@router.get("/{scene_id}", response_model=SceneOut)
async def detail(heritage_id: ResourceId, scene_id: ResourceId, svc: SceneService = Depends(service)):
    return await svc.scene(heritage_id, scene_id)


@router.patch("/{scene_id}", response_model=SceneOut)
async def update_scene(heritage_id: ResourceId, scene_id: ResourceId, data: SceneUpdate,
                       svc: SceneService = Depends(service)):
    return await svc.update(heritage_id, scene_id, data)


@router.delete("/{scene_id}", status_code=204)
async def delete_scene(heritage_id: ResourceId, scene_id: ResourceId, svc: SceneService = Depends(service)):
    await svc.delete(heritage_id, scene_id)
    return Response(status_code=204)
