import asyncio
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import threading

from sqlalchemy import select, text

from apps.backend.models.heritage_classification import ClassificationJob, CulturalContent, HeritageClassification
from apps.backend.services.classification_store import manual_override
from apps.backend.services.classification_worker import run_next
from apps.backend.services.classification_backfill import backfill, rollback
from apps.backend.tests import catalog_postgres_support as fixtures


class CatalogPostgresTests(fixtures.CatalogPostgresFixture):
    async def test_direct_sql_insert_update_idempotence_and_rollback(self):
        heritage_id = await self.heritage()
        async with self.factory() as db:
            content = (await db.scalars(select(CulturalContent))).one()
            self.assertEqual(content.input_revision, 1)
            self.assertEqual((await db.get(ClassificationJob, content.id)).status, "PENDING")
        self.assertTrue(await run_next(self.factory))
        async with self.factory() as db:
            keys = (await db.scalars(select(HeritageClassification.category_key))).all()
            self.assertEqual(set(keys), {"religious_site", "architecture"})
        async with self.engine.begin() as conn:
            await conn.execute(text("UPDATE heritage SET title=title WHERE id=:id"), {"id": heritage_id})
            self.assertEqual(await conn.scalar(text("SELECT input_revision FROM heritage_content")), 1)
        async with self.factory() as db:
            await db.execute(text("UPDATE heritage SET title='Lễ hội thử nghiệm' WHERE id=:id"), {"id": heritage_id})
            await db.rollback()
        self.assertFalse(await run_next(self.factory))
        async with self.engine.begin() as conn:
            await conn.execute(text("UPDATE heritage SET title='Bảo tàng thử nghiệm' WHERE id=:id"), {"id": heritage_id})
        self.assertTrue(await run_next(self.factory))
        async with self.factory() as db:
            row = (await db.scalars(select(CulturalContent))).one()
            self.assertEqual(row.input_revision, 2)
            self.assertEqual(row.classified_revision, 2)
            self.assertEqual((await db.scalars(select(HeritageClassification.category_key))).all(), ["museum"])
            self.assertEqual(await db.scalar(text("SELECT count(*) FROM heritage_classification_jobs")), 1)

    async def test_manual_lock_survives_sql_source_change(self):
        await self.heritage()
        await run_next(self.factory)
        async with self.factory() as db:
            content_id = await db.scalar(select(CulturalContent.id))
            await manual_override(db, content_id, SimpleNamespace(expected_revision=1, entity_type="place",
                categories=["historical_site"], primary_category="historical_site", locked=True,
                reasoning_summary="Reviewed source establishes this classification."), "1")
        async with self.engine.begin() as conn:
            await conn.execute(text("UPDATE heritage SET title='Bảo tàng mới'"))
        await run_next(self.factory)
        async with self.factory() as db:
            content = await db.get(CulturalContent, content_id)
            self.assertTrue(content.locked_by_admin)
            self.assertEqual(content.classified_revision, content.input_revision)
            self.assertEqual((await db.scalars(select(HeritageClassification.category_key))).all(), ["historical_site"])

    async def test_two_workers_claim_once_and_retry_without_private_errors(self):
        await self.heritage()
        results = await asyncio.gather(run_next(self.factory), run_next(self.factory))
        self.assertEqual(sum(results), 1)
        async with self.engine.begin() as conn:
            await conn.execute(text("UPDATE heritage SET description='Changed'"))
        def fail(*args, **kwargs):
            raise RuntimeError("secret-password https://private.example")
        await run_next(self.factory, classifier=fail)
        async with self.factory() as db:
            job = (await db.scalars(select(ClassificationJob))).one()
            self.assertEqual(job.status, "RETRY")
            self.assertNotIn("secret-password", job.last_error)
            self.assertEqual(job.attempts, 1)

    async def test_backfill_preview_apply_idempotence_and_guarded_rollback(self):
        await self.heritage()
        preview = await backfill(self.factory)
        self.assertTrue(preview["dry_run"])
        async with self.factory() as db:
            self.assertEqual(await db.scalar(text("SELECT count(*) FROM heritage_classifications")), 0)
        applied = await backfill(self.factory, apply=True)
        self.assertEqual(applied["items"][0]["action"], "APPLIED")
        unchanged = await backfill(self.factory, apply=True)
        self.assertEqual(unchanged["items"][0]["action"], "UNCHANGED")
        restored = await rollback(self.factory, applied["run_id"])
        self.assertEqual(restored["items"][0]["action"], "ROLLED_BACK")
        applied = await backfill(self.factory, apply=True)
        async with self.engine.begin() as conn:
            await conn.execute(text("UPDATE heritage SET description='New revision'"))
        conflict = await rollback(self.factory, applied["run_id"])
        self.assertEqual(conflict["items"][0]["action"], "SKIP_CONFLICT")

    async def test_source_edit_during_inference_cannot_finish_the_newer_job(self):
        await self.heritage()
        started, release = threading.Event(), threading.Event()
        from apps.backend.services.heritage_classifier import classify
        def delayed(source, **kwargs):
            started.set()
            if not release.wait(10):
                raise RuntimeError("test worker timeout")
            return classify(source)
        work = asyncio.create_task(run_next(self.factory, classifier=delayed))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 5))
            async with self.engine.begin() as conn:
                await conn.execute(text("UPDATE heritage SET title='Bảo tàng thay đổi'"))
        finally:
            release.set()
            await work
        async with self.factory() as db:
            job = (await db.scalars(select(ClassificationJob))).one()
            self.assertEqual((job.generation, job.status), (2, "PENDING"))
        await run_next(self.factory)
        async with self.factory() as db:
            self.assertEqual((await db.scalars(select(HeritageClassification.category_key))).all(), ["museum"])

    async def test_expired_crash_lease_is_recovered_without_duplicate_classifications(self):
        await self.heritage()
        async with self.engine.begin() as conn:
            await conn.execute(text("UPDATE heritage_classification_jobs SET status='RUNNING',attempts=1,leased_until=:expired"),
                               {"expired": datetime.now(timezone.utc) - timedelta(seconds=1)})
        self.assertTrue(await run_next(self.factory))
        async with self.factory() as db:
            job = (await db.scalars(select(ClassificationJob))).one()
            self.assertEqual((job.status, job.attempts), ("DONE", 2))
            self.assertEqual(await db.scalar(text("SELECT count(*) FROM heritage_classifications")), 2)
