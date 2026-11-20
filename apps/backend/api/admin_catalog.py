"""Source-backed editorial entities, review queue and locked classification API."""
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from apps.backend.api.catalog import get_db
from apps.backend.core.security import require_admin
from apps.backend.models.heritage_classification import ClassificationJob, ContentRelation, CulturalContent
from apps.backend.schemas.catalog import ClassificationOverride, ContentCreate, ContentPatch, RelationCreate
from apps.backend.services.classification_store import manual_override, snapshot

ResourceId = Annotated[int, Path(gt=0, lt=2**63)]


async def current_admin(user=Depends(require_admin), db=Depends(get_db)):
    try:
        account_id = int(user["sub"])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(401, "Invalid administrative account.") from None
    account = (await db.execute(text("SELECT a.is_active,a.locked_until,r.name FROM account a "
        "JOIN roles r ON r.id=a.role_id WHERE a.id=:id"), {"id": account_id})).mappings().one_or_none()
    if not account or not account["is_active"] or (account["locked_until"] and account["locked_until"] > datetime.now(timezone.utc)):
        raise HTTPException(401, "Administrative account unavailable.")
    if account["name"].lower() != "admin":
        raise HTTPException(403, "Current administrator permission required.")
    return str(account_id)


router = APIRouter(prefix="/admin/catalog", tags=["Admin heritage catalog"], dependencies=[Depends(current_admin)])


async def locate(db, content_id):
    content = (await db.scalars(select(CulturalContent).where(CulturalContent.id == content_id).with_for_update())).one_or_none()
    if content is None:
        raise HTTPException(404, "Catalog content not found.")
    return content


async def output(db, content):
    return {"id": content.id, "slug": content.slug, "title": content.title,
        "source_heritage_id": content.source_heritage_id, "input_revision": content.input_revision,
        "publish_state": content.publish_state, "is_featured": content.is_featured,
        "featured_rank": content.featured_rank, **await snapshot(db, content)}


async def commit(db):
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug, source reference or relation conflicts with existing data.") from None


@router.get("/contents")
async def review_queue(status: Literal["pending", "applied", "review", "unclassified"] | None = None,
                       limit: Annotated[int, Query(ge=1, le=100)] = 20,
                       after_id: Annotated[int, Query(ge=0)] = 0, db=Depends(get_db)):
    stmt = select(CulturalContent).where(CulturalContent.id > after_id).order_by(CulturalContent.id).limit(limit + 1)
    if status:
        stmt = stmt.where(CulturalContent.classification_status == status)
    rows = list((await db.scalars(stmt)).all())
    # Review summaries deliberately omit per-card nested classification queries.
    return {"items": [{"id": row.id, "slug": row.slug, "title": row.title,
        "input_revision": row.input_revision, "classification_status": row.classification_status,
        "locked_by_admin": row.locked_by_admin} for row in rows[:limit]],
        "next_after_id": rows[limit - 1].id if len(rows) > limit else None}


@router.get("/contents/{content_id}")
async def content_detail(content_id: ResourceId, db=Depends(get_db)):
    content = await locate(db, content_id)
    return {**await output(db, content), "source_url": content.source_url,
        "entity_type_hint": content.entity_type_hint, "verified_metadata": content.verified_metadata,
        "description": content.description, "card_image_url": content.card_image_url}


@router.post("/contents", status_code=201)
async def create_content(data: ContentCreate, db=Depends(get_db)):
    content = CulturalContent(**data.model_dump(mode="json", exclude_none=True))
    db.add(content)
    await commit(db)
    await db.refresh(content)
    return await output(db, content)


@router.patch("/contents/{content_id}")
async def update_content(content_id: ResourceId, data: ContentPatch, db=Depends(get_db)):
    content = await locate(db, content_id)
    if content.input_revision != data.expected_revision:
        raise HTTPException(409, "Content changed; reload before editing.")
    values = data.model_dump(mode="json", exclude_unset=True, exclude={"expected_revision"})
    if content.source_heritage_id is not None and set(values) - {"is_featured", "featured_rank", "verified_metadata", "source_url"}:
        raise HTTPException(422, "Edit source heritage text/publication/media on heritage; the catalog is its projection.")
    for key, value in values.items():
        setattr(content, key, value)
    await commit(db)
    await db.refresh(content)  # Read revisions incremented by the database trigger.
    return await output(db, content)


@router.put("/contents/{content_id}/classification")
async def classify_manually(content_id: ResourceId, data: ClassificationOverride,
                            actor=Depends(current_admin), db=Depends(get_db)):
    return await manual_override(db, content_id, data, actor)


@router.post("/contents/{content_id}/reclassify", status_code=202)
async def reclassify(content_id: ResourceId, db=Depends(get_db)):
    content = await locate(db, content_id)
    # Locked overrides remain locked; requeueing cannot bypass the reviewer.
    await db.execute(text("""INSERT INTO heritage_classification_jobs(content_id,generation)
        VALUES(:id,:generation) ON CONFLICT(content_id) DO UPDATE SET status='PENDING',attempts=0,
        generation=EXCLUDED.generation,available_at=now(),leased_until=NULL,lease_token=NULL,last_error=NULL"""),
        {"id": content_id, "generation": content.input_revision})
    await commit(db)
    return {"content_id": content_id, "status": "PENDING", "locked_by_admin": content.locked_by_admin}


@router.get("/contents/{content_id}/job")
async def job_status(content_id: ResourceId, db=Depends(get_db)):
    job = await db.get(ClassificationJob, content_id)
    if job is None:
        raise HTTPException(404, "Classification job not found.")
    return {"content_id": content_id, "generation": job.generation, "status": job.status,
            "attempts": job.attempts, "available_at": job.available_at, "last_error": job.last_error}


@router.post("/contents/{content_id}/relations", status_code=201)
async def relate(content_id: ResourceId, data: RelationCreate, db=Depends(get_db)):
    await locate(db, content_id)
    if content_id == data.object_id:
        raise HTTPException(422, "An entity cannot relate to itself.")
    if await db.get(CulturalContent, data.object_id) is None:
        raise HTTPException(422, "Related content does not exist.")
    db.add(ContentRelation(subject_id=content_id, **data.model_dump()))
    await commit(db)
    return {"subject_id": content_id, **data.model_dump()}
