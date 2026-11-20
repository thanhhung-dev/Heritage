"""Preview, audit and guarded rollback of catalog classifications only."""
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import select

from apps.backend.models.heritage_classification import ClassificationAudit, ClassificationJob, CulturalContent
from apps.backend.services.classification_store import apply_prediction, record_audit, restore_snapshot, snapshot
from apps.backend.services.classification_input import classification_input
from apps.backend.services.heritage_classifier import ContentInput, classify, decision


async def backfill(factory, *, apply=False, limit=1000, after_id=0, high=0.9, medium=0.55):
    run_id = str(uuid4())
    async with factory() as db:
        rows = list((await db.scalars(select(CulturalContent).where(CulturalContent.id > after_id)
            .order_by(CulturalContent.id).limit(limit))).all())
        inputs = [(row.id, row.input_revision, row.locked_by_admin, await classification_input(db, row)) for row in rows]
    changes = []
    for content_id, revision, locked, source in inputs:
        prediction = classify(source)
        item = {"id": content_id, "title": source.title, "revision": revision,
                "entity_type": prediction.entity_type, "categories": list(prediction.categories),
                "primary_category": prediction.primary_category, "confidence": prediction.confidence,
                "decision": decision(prediction, high, medium), "action": "SKIP_LOCKED" if locked else "PREVIEW"}
        if apply and not locked:
            async with factory() as db:
                content = (await db.scalars(select(CulturalContent).where(CulturalContent.id == content_id).with_for_update())).one_or_none()
                if content is None or content.input_revision != revision:
                    item["action"] = "SKIP_CHANGED"
                elif content.locked_by_admin:
                    item["action"] = "SKIP_LOCKED"
                else:
                    job = (await db.scalars(select(ClassificationJob).where(
                        ClassificationJob.content_id == content_id).with_for_update())).one_or_none()
                    if job and job.status == "RUNNING" and job.leased_until and job.leased_until > datetime.now(timezone.utc):
                        item["action"] = "SKIP_BUSY"
                    else:
                        before = await snapshot(db, content)
                        expected = {(key, key == prediction.primary_category) for key in prediction.categories}
                        existing = {(row["category_key"], row["is_primary"]) for row in before["categories"]}
                        if (content.classified_revision == revision and content.entity_type == prediction.entity_type
                                and content.classification_status == item["decision"] and expected == existing):
                            item["action"] = "UNCHANGED"
                        else:
                            await apply_prediction(db, content, prediction, run_id=run_id, high=high, medium=medium, actor="backfill")
                            item["action"] = "APPLIED"
                        if job:
                            job.status, job.lease_token, job.leased_until, job.last_error = "DONE", None, None, None
                        await db.commit()
        changes.append(item)
    return {"run_id": run_id, "dry_run": not apply, "items": changes,
            "next_after_id": inputs[-1][0] if len(inputs) == limit else None}


async def rollback(factory, run_id):
    rollback_id = str(uuid4())
    async with factory() as db:
        audits = list((await db.scalars(select(ClassificationAudit).where(
            ClassificationAudit.run_id == run_id, ClassificationAudit.actor == "backfill")
            .order_by(ClassificationAudit.id.desc()))).all())
    outcomes = []
    for audit in audits:
        async with factory() as db:
            content = (await db.scalars(select(CulturalContent).where(CulturalContent.id == audit.content_id)
                .with_for_update())).one_or_none()
            if (content is None or content.input_revision != audit.input_revision
                    or await snapshot(db, content) != audit.after):
                outcomes.append({"id": audit.content_id, "action": "SKIP_CONFLICT"})
                continue
            before = await snapshot(db, content)
            await restore_snapshot(db, content, audit.before)
            job = await db.get(ClassificationJob, content.id, with_for_update=True)
            if job:
                job.status, job.lease_token, job.leased_until = "DONE", None, None
            await record_audit(db, content, before, "rollback:" + run_id, rollback_id)
            await db.commit()
            outcomes.append({"id": content.id, "action": "ROLLED_BACK"})
    return {"run_id": rollback_id, "rollback_of": run_id, "items": outcomes}
