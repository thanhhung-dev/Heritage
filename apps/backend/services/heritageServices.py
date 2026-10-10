from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.models.heritage import Heritage


class HeritageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_published(self) -> list[Heritage]:
        stmt = (
            select(Heritage)
            .where(Heritage.publish_state == 1)
            .options(
                selectinload(Heritage.voices),
                selectinload(Heritage.language1),
                selectinload(Heritage.language2),
            )
            .order_by(Heritage.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_by_slug(self, slug: str) -> Heritage | None:
        stmt = (
            select(Heritage)
            .where(Heritage.slug == slug, Heritage.publish_state == 1)
            .options(
                selectinload(Heritage.voices),
                selectinload(Heritage.language1),
                selectinload(Heritage.language2),
            )
        )
        return (await self.db.execute(stmt)).scalars().first()