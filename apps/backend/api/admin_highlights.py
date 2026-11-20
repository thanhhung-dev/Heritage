"""Admin API for assigning stable identities to interactive markers."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.search import PassageStore, SearchError
from apps.backend.core.security import require_admin
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.models.heritage import Heritage
from apps.backend.models.interactive import Interactive
from apps.backend.models.interactive_highlight import InteractiveHighlight
from apps.backend.models.interactive_highlight_passage import InteractiveHighlightPassage
from apps.backend.models.scene import Scene
from apps.backend.services.tour_passages import matches_reviewed_passage
from apps.backend.services.tour_scope import resolve_area

router = APIRouter(
    prefix="/admin/interactive-highlights",
    tags=["Admin interactive highlights"],
    dependencies=[Depends(require_admin)],
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


class PassageLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    passage_id: str = Field(min_length=1, max_length=512)

    @field_validator("passage_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value.strip() or "\x00" in value or len(value.encode()) > 512:
            raise ValueError("ID passage phải từ 1 đến 512 byte và không chứa ký tự NUL.")
        return value


class PassageLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    highlight_id: int
    passage_id: str
    content_hash: str
    object_key: str
    bucket: str


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


@router.get("/{highlight_id}/passages", response_model=list[PassageLinkOut])
async def list_passage_links(highlight_id: int, db: AsyncSession = Depends(get_db)):
    if await db.get(InteractiveHighlight, highlight_id) is None:
        raise HTTPException(404, "Không tìm thấy interactive highlight.")
    rows = await db.scalars(select(InteractiveHighlightPassage).where(
        InteractiveHighlightPassage.highlight_id == highlight_id,
    ).order_by(InteractiveHighlightPassage.passage_id))
    return list(rows.all())


@router.post("/{highlight_id}/passages", response_model=PassageLinkOut, status_code=201)
async def link_passage(highlight_id: int, data: PassageLinkCreate, db: AsyncSession = Depends(get_db)):
    slug = (await db.execute(select(Heritage.slug).select_from(InteractiveHighlight)
        .join(Interactive, Interactive.id == InteractiveHighlight.interactive_id)
        .join(Scene, Scene.id == Interactive.scene_id)
        .join(Heritage, Heritage.id == Scene.heritage_id)
        .where(InteractiveHighlight.id == highlight_id))).scalar_one_or_none()
    if slug is None:
        raise HTTPException(404, "Không tìm thấy interactive highlight.")
    try:
        area = resolve_area(slug).id
    except ValueError:
        raise HTTPException(422, "Di sản của điểm chưa thuộc khu vực được hỗ trợ.") from None
    try:
        async with PassageStore() as store:
            rows = await store.get_passages([data.passage_id], active_area_id=area)
    except SearchError:
        raise HTTPException(503, "Không thể kiểm tra passage trong OpenSearch.") from None
    if not rows:
        raise HTTPException(422, "Passage không tồn tại hoặc không thuộc khu vực hiện tại.")
    row = rows[0]
    provenance = {"content_hash": row.get("content_hash", ""),
                  "object_key": row.get("object_key", ""), "bucket": row.get("bucket", "")}
    if (row["id"] != data.passage_id or row.get("active_area_id") != area
            or not all(isinstance(value, str) for value in provenance.values())
            or not matches_reviewed_passage(row, provenance)):
        raise HTTPException(422, "Passage thiếu nội dung, hash hoặc thông tin khu vực hợp lệ.")
    link = InteractiveHighlightPassage(highlight_id=highlight_id, passage_id=data.passage_id, **provenance)
    db.add(link)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Passage đã được liên kết với điểm này.") from None
    return link


@router.delete("/{highlight_id}/passages", status_code=204)
async def unlink_passage(highlight_id: int, passage_id: str = Query(min_length=1, max_length=512),
                         db: AsyncSession = Depends(get_db)):
    link = await db.get(InteractiveHighlightPassage, (highlight_id, passage_id))
    if link is None:
        raise HTTPException(404, "Không tìm thấy liên kết passage.")
    await db.delete(link)
    await db.commit()
    return Response(status_code=204)
