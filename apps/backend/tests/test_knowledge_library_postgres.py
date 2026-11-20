"""Actual PostgreSQL locks/constraints in an explicitly owned, disposable schema."""
import asyncio
import importlib.util
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from apps.backend.core.r2_library import KnowledgeR2
from apps.backend.models.knowledge_library import LibraryUpload
from apps.backend.schemas.knowledge_library import UploadRequest
from apps.backend.services.knowledge_library import KnowledgeLibrary
from apps.backend.tests.knowledge_library_support import MemoryR2


class KnowledgePostgresTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def asyncSetUp(self):
        raw = os.environ.get("KNOWLEDGE_TEST_DATABASE_URL")
        if not raw:
            self.skipTest("explicit KNOWLEDGE_TEST_DATABASE_URL required")
        url = make_url(raw)
        if (url.drivername != "postgresql+psycopg" or url.host not in {"localhost", "127.0.0.1", "::1"}
                or not (url.database or "").startswith("test_")):
            self.fail("Only an explicit loopback postgresql+psycopg test_* database is permitted")
        self.enterContext(patch.dict(os.environ,
            {"R2_KNOWLEDGE_BUCKET": "knowledge-heritage", "R2_KNOWLEDGE_LIBRARY_PREFIX": ""}))
        self.schema = "knowledge_test_" + uuid4().hex
        self.engine = create_async_engine(url, poolclass=NullPool,
            connect_args={"options": "-csearch_path=" + self.schema})
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addAsyncCleanup(self.drop_owned_schema)
        async with self.engine.begin() as conn:
            def migrate(connection):
                from alembic.migration import MigrationContext
                from alembic.operations import Operations
                path = Path(__file__).parents[1] / "migrations/versions/20261120_10_knowledge_library.py"
                spec = importlib.util.spec_from_file_location("knowledge_migration_test", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                with Operations.context(MigrationContext.configure(connection)):
                    module.upgrade()
            await conn.run_sync(migrate)
        self.s3, self.data = MemoryR2(), UploadRequest(folder="test/", filename="sample.txt", contentType="text/plain", size=5)
        self.storage = KnowledgeR2(client=self.s3)

    async def drop_owned_schema(self):
        # Identifier was generated here, never accepted from configuration.
        self.assertTrue(self.schema.startswith("knowledge_test_"))
        self.assertEqual(len(self.schema), len("knowledge_test_") + 32)
        async with self.engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    async def begin(self):
        async with self.factory() as db:
            return await KnowledgeLibrary(db, self.storage).begin_upload(self.data, 1)

    async def stage(self, result):
        async with self.factory() as db:
            upload = await db.get(LibraryUpload, result["uploadId"])
        self.s3.seed(upload.staging_key, b"hello", "text/plain", {"upload-id": upload.id})
        return upload

    async def test_migration_creates_only_upload_table_with_constraints_and_indexes(self):
        async with self.engine.connect() as conn:
            tables, indexes = await conn.run_sync(lambda c: (inspect(c).get_table_names(),
                inspect(c).get_indexes("knowledge_library_upload")))
            self.assertEqual(tables, ["knowledge_library_upload"])
            self.assertIn("ix_library_expiry", {i["name"] for i in indexes})
        result = await self.begin()
        async with self.factory() as db:
            with self.assertRaises(IntegrityError):
                await db.execute(text("UPDATE knowledge_library_upload SET bucket='heritage' WHERE id=:id"), {"id": result["uploadId"]})
            await db.rollback()
            with self.assertRaises(IntegrityError):
                await db.execute(text("UPDATE knowledge_library_upload SET reservation_key=NULL WHERE id=:id"), {"id": result["uploadId"]})

    async def test_concurrent_destination_reservation_has_one_winner(self):
        results = await asyncio.gather(self.begin(), self.begin(), return_exceptions=True)
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1, results)
        errors = [r for r in results if isinstance(r, HTTPException)]
        self.assertEqual([e.status_code for e in errors], [409], results)

    async def test_concurrent_completion_on_separate_connections_publishes_once(self):
        result = await self.begin()
        upload = await self.stage(result)
        async def complete():
            async with self.factory() as db:
                return await KnowledgeLibrary(db, self.storage).complete(upload.id, 1)
        results = await asyncio.gather(complete(), complete())
        self.assertEqual([r["uploadId"] for r in results], [upload.id, upload.id])
        writes = [c for c in self.s3.calls if c[0] == "put" and c[1]["Key"] == upload.final_key]
        self.assertEqual(len(writes), 1)

    async def test_publication_survives_database_transaction_rollback_and_expiry(self):
        result = await self.begin()
        upload = await self.stage(result)
        # Simulate a worker terminating between R2 publication and database commit.
        self.storage.publish_verified(upload)
        async with self.factory() as db:
            await db.execute(text("UPDATE knowledge_library_upload SET expires_at=:expiry WHERE id=:id"),
                {"expiry": datetime.now(timezone.utc) - timedelta(seconds=1), "id": upload.id})
            await db.commit()
        async with self.factory() as db:
            recovered = await KnowledgeLibrary(db, self.storage).complete(upload.id, 1)
            self.assertEqual(recovered["object"]["key"], upload.final_key)
        self.assertEqual(len([c for c in self.s3.calls if c[0] == "put" and c[1]["Key"] == upload.final_key]), 1)

    async def test_completed_destination_can_be_reused_only_after_explicit_deletion(self):
        result = await self.begin()
        upload = await self.stage(result)
        async with self.factory() as db:
            await KnowledgeLibrary(db, self.storage).complete(upload.id, 1)
        self.storage.delete_file(upload.final_key)  # Synthetic R2 only.
        newer = await self.begin()
        self.assertNotEqual(newer["uploadId"], upload.id)
        async with self.factory() as db:
            with self.assertRaises(HTTPException) as error:
                await KnowledgeLibrary(db, self.storage).complete(upload.id, 1)
            self.assertEqual(error.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
