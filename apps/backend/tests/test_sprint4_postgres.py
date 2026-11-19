"""Opt-in live PostgreSQL checks, restricted to an explicitly named test database.

Set SPRINT4_POSTGRES_TEST_URL to an async PostgreSQL URL whose database name
starts with test_ or ends with _test. Only a random schema owned by this test
is created/dropped. Never falls back to the application's DATABASE_URL.
"""
import asyncio
import os
from pathlib import Path
import unittest
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from apps.backend.schemas.admin_scene import SceneOrder
from apps.backend.schemas.rag_pipeline import PipelineCreate, PipelineUpdate
from apps.backend.services.admin_scene import SceneService
from apps.backend.services.rag_pipeline import PipelineService


@unittest.skipUnless(os.environ.get("SPRINT4_POSTGRES_TEST_URL"), "explicit disposable PostgreSQL test database required")
class Sprint4PostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = make_url(os.environ["SPRINT4_POSTGRES_TEST_URL"])
        if (url.drivername != "postgresql+psycopg" or not url.database
                or not (url.database.startswith("test_") or url.database.endswith("_test"))):
            self.fail("Use postgresql+psycopg and a database named test_* or *_test")
        self.schema = "sprint4_test_" + uuid4().hex
        self.engine = create_async_engine(url, poolclass=NullPool,
            connect_args={"options": f"-csearch_path={self.schema}"})
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addAsyncCleanup(self.drop_schema)
        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE TABLE account(id BIGINT PRIMARY KEY, is_active BOOLEAN NOT NULL DEFAULT TRUE)"))
            for name in ("2026-11-19_account_token_version.sql", "2026-11-19_rag_pipeline.sql"):
                script = (Path(__file__).parents[1] / "migrations" / name).read_text(encoding="utf-8")
                for statement in script.split(";"):
                    if statement.strip():
                        await conn.execute(text(statement))
            await conn.execute(text("CREATE TABLE heritage(id BIGINT PRIMARY KEY)"))
            await conn.execute(text("""CREATE TABLE scene(
                id BIGINT PRIMARY KEY, heritage_id BIGINT NOT NULL REFERENCES heritage(id),
                sequence INTEGER NOT NULL CHECK(sequence >= -1), title TEXT NOT NULL, description TEXT,
                sky_preset_id BIGINT, camera_node_name TEXT, cam_start_pos JSONB, cam_start_target JSONB,
                cam_zoom_pos JSONB, cam_zoom_target JSONB, camera_path_url TEXT, instant_move BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT now(), UNIQUE(heritage_id,sequence))"""))
            await conn.execute(text("INSERT INTO heritage VALUES(1)"))
            await conn.execute(text("INSERT INTO scene(id,heritage_id,sequence,title) VALUES(1,1,0,'First'),(2,1,1,'Second')"))
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def drop_schema(self):
        # self.schema is generated here, never taken from a URL or user input.
        async with self.engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    async def test_additive_migrations_and_pipeline_json_crud(self):
        async with self.factory() as db:
            await db.execute(text("INSERT INTO account(id) VALUES(1)"))
            self.assertEqual(await db.scalar(text("SELECT token_version FROM account WHERE id=1")), 0)
            await db.commit()
            service = PipelineService(db)
            pipeline = await service.create(PipelineCreate(name="PostgreSQL"))
            updated = await service.update(pipeline.id, PipelineUpdate(expected_revision=1, retrieval={"top_k": 7}))
            self.assertEqual(updated.retrieval.top_k, 7)
            self.assertEqual(updated.revision, 2)
            await service.delete(pipeline.id)

    async def test_concurrent_reorder_serializes_and_rejects_stale_writer(self):
        async def reorder():
            async with self.factory() as db:
                try:
                    await SceneService(db).reorder(1, SceneOrder(scene_ids=[2, 1], expected_scene_ids=[1, 2]))
                    return 200
                except HTTPException as error:
                    return error.status_code
        results = await asyncio.gather(reorder(), reorder())
        self.assertEqual(sorted(results), [200, 409])
        async with self.factory() as db:
            rows = (await db.execute(text("SELECT id,sequence FROM scene ORDER BY sequence"))).all()
            self.assertEqual([tuple(row) for row in rows], [(2, 0), (1, 1)])
