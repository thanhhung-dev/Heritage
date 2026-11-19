"""Admin API for assigning stable identities to interactive markers."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import require_admin
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.models.interactive import Interactive
from apps.backend.models.interactive_highlight import InteractiveHighlight

router = APIRouter(
    prefix="/admin/interactive-highlights",
    tags=["Admin interactive highlights"],
)
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class ArtifactKeyPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artifact_key: str | None = Field(default=None, max_length=120)

    @field_validator("artifact_key")
    @classmethod
    def validate_artifact_key(cls, value: str | None) -> str | None:
        if value is not None and not _SLUG.fullmatch(value):
            raise ValueError("artifact_key phải là slug chữ thường, ví dụ thanh-hien-vat-001.")
        return value


class InteractiveHighlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interactive_id: int
    popup_title: str | None
    artifact_key: str | None


async def get_db():
    if AsyncSessionLocal.kw.get("bind") is None:
        raise HTTPException(503, "Database chưa được cấu hình.")
    async with AsyncSessionLocal() as session:
        yield session


@router.get("", response_model=list[InteractiveHighlightOut])
async def list_interactive_highlights(
    scene_id: int | None = Query(default=None, gt=0),
    db: AsyncSession = Depends(get_db),
):
    statement = select(InteractiveHighlight).join(Interactive).order_by(InteractiveHighlight.id)
    if scene_id is not None:
        statement = statement.where(Interactive.scene_id == scene_id)
    return list((await db.scalars(statement)).all())


@router.patch("/{highlight_id}", response_model=InteractiveHighlightOut)
async def patch_interactive_highlight(
    highlight_id: int,
    data: ArtifactKeyPatch,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    highlight = await db.get(InteractiveHighlight, highlight_id)
    if highlight is None:
        raise HTTPException(404, "Không tìm thấy interactive highlight.")
    highlight.artifact_key = data.artifact_key
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "artifact_key đã được gán cho marker khác.") from None
    await db.refresh(highlight)
    return highlight
