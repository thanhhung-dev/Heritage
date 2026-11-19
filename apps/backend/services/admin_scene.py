"""Scene mutation is serialized by its existing heritage parent row."""
from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.models.heritage import Heritage
from apps.backend.models.scene import Scene
from apps.backend.schemas.admin_scene import SceneCreate, SceneOrder, SceneOut, SceneUpdate


class SceneService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def heritage(self, heritage_id, *, lock=False):
        stmt = select(Heritage.id).where(Heritage.id == heritage_id)
        if lock:
            stmt = stmt.with_for_update()
        if await self.db.scalar(stmt) is None:
            raise HTTPException(404, "Heritage not found.")

    async def scene(self, heritage_id, scene_id):
        row = (await self.db.scalars(select(Scene).where(
            Scene.id == scene_id, Scene.heritage_id == heritage_id))).one_or_none()
        if row is None:
            raise HTTPException(404, "Scene not found in this heritage.")
        return row

    async def list(self, heritage_id, after_sequence, limit):
        await self.heritage(heritage_id)
        stmt = select(Scene).where(Scene.heritage_id == heritage_id).order_by(Scene.sequence).limit(limit + 1)
        if after_sequence is not None:
            stmt = stmt.where(Scene.sequence > after_sequence)
        rows = list((await self.db.scalars(stmt)).all())
        return {"items": [SceneOut.model_validate(row) for row in rows[:limit]],
                "next_after_sequence": rows[limit - 1].sequence if len(rows) > limit else None}

    async def commit(self):
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(409, "Scene sequence or relationship conflicts with current data.") from None

    async def create(self, heritage_id, data: SceneCreate):
        await self.heritage(heritage_id, lock=True)
        sequence = data.sequence
        if sequence is None:
            maximum = await self.db.scalar(select(func.max(Scene.sequence)).where(Scene.heritage_id == heritage_id))
            sequence = max(0, (maximum if maximum is not None else -1) + 1)
        if sequence > 2**31 - 1:
            raise HTTPException(409, "Scene sequence exhausted; reorder scenes first.")
        row = Scene(heritage_id=heritage_id, title=data.title, description=data.description,
                    sequence=sequence, instant_move=False)
        self.db.add(row)
        await self.commit()
        return SceneOut.model_validate(row)

    async def update(self, heritage_id, scene_id, data: SceneUpdate):
        await self.heritage(heritage_id, lock=True)
        row = await self.scene(heritage_id, scene_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await self.commit()
        return SceneOut.model_validate(row)

    async def delete(self, heritage_id, scene_id):
        await self.heritage(heritage_id, lock=True)
        await self.scene(heritage_id, scene_id)
        # Rely on the schema's child cascades; no remote object operation occurs.
        await self.db.execute(delete(Scene).where(Scene.id == scene_id, Scene.heritage_id == heritage_id))
        await self.commit()

    async def reorder(self, heritage_id, data: SceneOrder):
        await self.heritage(heritage_id, lock=True)
        scenes = list((await self.db.scalars(select(Scene).where(
            Scene.heritage_id == heritage_id, Scene.sequence >= 0).order_by(Scene.sequence))).all())
        current = [row.id for row in scenes]
        if current != data.expected_scene_ids:
            raise HTTPException(409, "Scene order changed; reload before reordering.")
        if set(current) != set(data.scene_ids):
            raise HTTPException(422, "scene_ids must contain every non-overview scene of this heritage exactly once.")
        # Move into unused positive slots first, satisfying immediate UNIQUE and
        # CHECK constraints even during swaps. The whole transaction stays locked.
        temporary = max((row.sequence for row in scenes), default=-1) + 1
        if temporary + len(scenes) > 2**31 - 1:
            raise HTTPException(409, "Insufficient temporary sequence space for reordering.")
        for offset, scene_id in enumerate(data.scene_ids):
            await self.db.execute(update(Scene).where(Scene.id == scene_id).values(sequence=temporary + offset))
        for sequence, scene_id in enumerate(data.scene_ids):
            await self.db.execute(update(Scene).where(Scene.id == scene_id).values(sequence=sequence))
        await self.commit()
        return {"items": [SceneOut.model_validate(row) for row in sorted(scenes, key=lambda row: row.sequence)],
                "next_after_sequence": None}
