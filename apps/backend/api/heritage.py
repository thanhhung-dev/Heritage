from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.db.base import AsyncSessionLocal
from apps.backend.schemas.heritage import HeritageOut
from apps.backend.services.heritageServices import HeritageService

router = APIRouter(prefix="/heritages", tags=["heritages"])


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def get_service(db: AsyncSession = Depends(get_db)) -> HeritageService:
    return HeritageService(db)


@router.get("", response_model=list[HeritageOut])
async def list_heritages(service: HeritageService = Depends(get_service)):
    return await service.list_published()


@router.get("/{slug}", response_model=HeritageOut)
async def get_heritage(slug: str, service: HeritageService = Depends(get_service)):
    heritage = await service.get_by_slug(slug)
    if not heritage:
        raise HTTPException(status_code=404, detail="Heritage not found")
    return heritage