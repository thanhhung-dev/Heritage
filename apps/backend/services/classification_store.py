"""Transactional application of predictions and locked editorial overrides."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select

from apps.backend.models.heritage_classification import (
    ClassificationAudit, CulturalContent, HeritageClassification,
)
from apps.backend.services.heritage_classifier import Prediction, decision
from apps.backend.services.heritage_taxonomy import validate_categories


async def snapshot(db, content):
    rows = (await db.scalars(select(HeritageClassification).where(
        HeritageClassification.content_id == content.id).order_by(HeritageClassification.category_key))).all()
    return {"entity_type": content.entity_type, "classification_status": content.classification_status,
        "classified_revision": content.classified_revision, "locked_by_admin": content.locked_by_admin,
        "categories": [{"category_key": row.category_key, "is_primary": row.is_primary,
            "confidence": row.confidence, "classification_source": row.classification_source,
            "reasoning_summary": row.reasoning_summary,
            "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None} for row in rows]}


async def record_audit(db, content, before, actor, run_id):
    after = await snapshot(db, content)
    db.add(ClassificationAudit(content_id=content.id, run_id=run_id, input_revision=content.input_revision,
                               actor=actor, before=before, after=after))
    return after


async def apply_prediction(db, content, prediction: Prediction, *, run_id, high=0.9, medium=0.55, actor="worker"):
    before = await snapshot(db, content)
    if not content.locked_by_admin:
        await db.execute(delete(HeritageClassification).where(HeritageClassification.content_id == content.id))
        content.entity_type = prediction.entity_type
        content.classification_status = decision(prediction, high, medium)
        for key in prediction.categories:
            db.add(HeritageClassification(content_id=content.id, category_key=key,
                is_primary=key == prediction.primary_category, confidence=prediction.confidence,
                classification_source=prediction.classification_source,
                reasoning_summary=prediction.reasoning_summary))
    else:
        content.classification_status = "applied"
    content.classified_revision = content.input_revision
    await db.flush()
    return await record_audit(db, content, before, actor if not content.locked_by_admin else actor + ":locked", run_id)


async def restore_snapshot(db, content, state):
    await db.execute(delete(HeritageClassification).where(HeritageClassification.content_id == content.id))
    for row in state["categories"]:
        values = dict(row)
        if values.get("reviewed_at"):
            values["reviewed_at"] = datetime.fromisoformat(values["reviewed_at"])
        db.add(HeritageClassification(content_id=content.id, **values))
    for key in ("entity_type", "classification_status", "classified_revision", "locked_by_admin"):
        setattr(content, key, state[key])
    await db.flush()


async def manual_override(db, content_id, data, actor):
    content = (await db.scalars(select(CulturalContent).where(CulturalContent.id == content_id).with_for_update())).one_or_none()
    if content is None:
        raise HTTPException(404, "Catalog content not found.")
    if data.expected_revision != content.input_revision:
        raise HTTPException(409, "Content changed; reload before review.")
    if content.source_heritage_id is None and data.entity_type != content.entity_type_hint:
        raise HTTPException(422, "Review the independent entity type hint before changing its classification.")
    try:
        validate_categories(data.entity_type, data.categories, data.primary_category)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    before = await snapshot(db, content)
    await db.execute(delete(HeritageClassification).where(HeritageClassification.content_id == content_id))
    for key in data.categories:
        db.add(HeritageClassification(content_id=content_id, category_key=key,
            is_primary=key == data.primary_category, confidence=1.0, classification_source="manual",
            reasoning_summary=data.reasoning_summary, reviewed_at=datetime.now(timezone.utc)))
    content.entity_type, content.locked_by_admin = data.entity_type, data.locked
    content.classification_status, content.classified_revision = "applied", content.input_revision
    await db.flush()
    result = await record_audit(db, content, before, "admin:" + actor, str(uuid4()))
    await db.commit()
    return result
