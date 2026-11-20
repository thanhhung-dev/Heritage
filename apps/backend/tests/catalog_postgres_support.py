"""Owned-schema PostgreSQL fixture; never uses the application DB implicitly."""
import asyncio
import os
from pathlib import Path
import sys
import unittest
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from apps.backend.models.knowledge import KnowledgeDocument

ROOT = Path(__file__).resolve().parents[3]


class CatalogPostgresFixture(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def asyncSetUp(self):
        raw = os.environ.get("CATALOG_TEST_DATABASE_URL")
        if not raw:
            self.skipTest("explicit CATALOG_TEST_DATABASE_URL required")
        url = make_url(raw)
        if (url.drivername != "postgresql+psycopg" or url.host not in {"localhost", "127.0.0.1", "::1"}
                or not (url.database or "").startswith("test_")):
            self.fail("Use an explicit loopback postgresql+psycopg test_* database")
        self.schema = "catalog_test_" + uuid4().hex
        self.engine = create_async_engine(url, poolclass=NullPool,
            connect_args={"options": "-csearch_path=" + self.schema})
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addAsyncCleanup(self.drop_schema)
        async with self.engine.begin() as conn:
            await conn.exec_driver_sql((ROOT / "schema.sql").read_text(encoding="utf-8"))
            await conn.execute(text("CREATE TABLE entity(id UUID PRIMARY KEY)"))
            await conn.run_sync(KnowledgeDocument.__table__.create)
            await conn.exec_driver_sql((ROOT / "apps/backend/migrations/versions/20261120_09_heritage_classification.sql").read_text(encoding="utf-8"))

    async def drop_schema(self):
        async with self.engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    async def heritage(self, title="Chùa Thiên Mụ", description="Di sản kiến trúc.", published=True):
        async with self.engine.begin() as conn:
            return await conn.scalar(text("""INSERT INTO heritage(slug,title,description,publish_state,card_image_url)
                VALUES(:slug,:title,:description,:state,'images/test.jpg') RETURNING id"""),
                {"slug": "test-" + uuid4().hex, "title": title, "description": description,
                 "state": "published" if published else "draft"})
