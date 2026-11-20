"""Published classification-driven discovery; old heritage APIs stay intact."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from apps.backend.db.base import AsyncSessionLocal
from apps.backend.schemas.catalog import CatalogDetail, CatalogPage, CategoryOut, EntityType, SectionKey
from apps.backend.services.catalog import CatalogService, SECTION_KEYS
from apps.backend.services.heritage_taxonomy import BY_KEY

router = APIRouter(prefix="/catalog", tags=["Heritage catalog"])


async def get_db():
    if AsyncSessionLocal.kw.get("bind") is None:
        raise HTTPException(503, "Catalog database requires DATABASE_URL and migrations.")
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(503, "Catalog database unavailable; check migrations/configuration.") from None


def no_cache(response: Response):
    # Source triggers + worker commit are visible on the next query. Avoid stale
    # CDN/browser responses; the homepage refreshes while visible.
    response.headers["Cache-Control"] = "no-store"


async def public_db(db=Depends(get_db)):
    # Keep entity rows, categories and all section placements in one snapshot
    # while a background worker commits new classifications concurrently.
    await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    return db


@router.get("/categories", response_model=list[CategoryOut])
async def categories(response: Response, db=Depends(public_db)):
    no_cache(response)
    return await CatalogService(db).categories()


@router.get("/contents", response_model=CatalogPage)
async def contents(response: Response, category: str | None = None, entity_type: EntityType | None = None,
                   sort: Literal["title", "newest"] = "title",
                   limit: Annotated[int, Query(ge=1, le=100)] = 20,
                   offset: Annotated[int, Query(ge=0, le=10000)] = 0, db=Depends(public_db)):
    no_cache(response)
    if category and category not in BY_KEY:
        raise HTTPException(422, "Unknown taxonomy category.")
    return await CatalogService(db).page(category=category, entity_type=entity_type, sort=sort, limit=limit, offset=offset)


@router.get("/sections", response_model=dict[SectionKey, CatalogPage])
async def sections(response: Response, limit: Annotated[int, Query(ge=1, le=30)] = 8, db=Depends(public_db)):
    no_cache(response)
    service = CatalogService(db)
    # Sequential bounded reads share one session. Query count is independent of
    # the number of cards; there are no per-card document/voice queries.
    return {key: await service.page(section=key, limit=limit) for key in SECTION_KEYS}


@router.get("/sections/{section}", response_model=CatalogPage)
async def section_page(section: SectionKey, response: Response,
                       sort: Literal["title", "newest"] = "title",
                       limit: Annotated[int, Query(ge=1, le=100)] = 8,
                       offset: Annotated[int, Query(ge=0, le=10000)] = 0, db=Depends(public_db)):
    no_cache(response)
    return await CatalogService(db).page(section=section, sort=sort, limit=limit, offset=offset)


@router.get("/contents/{slug}", response_model=CatalogDetail)
async def detail(slug: str, response: Response, db=Depends(public_db)):
    no_cache(response)
    return await CatalogService(db).detail(slug)
