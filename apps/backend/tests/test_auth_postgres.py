"""Concurrent registration on an explicitly configured disposable PostgreSQL DB."""
import asyncio
import os
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from apps.backend.api import auth


class AuthPostgresTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def asyncSetUp(self):
        raw = os.environ.get("AUTH_TEST_DATABASE_URL")
        if not raw:
            self.skipTest("explicit AUTH_TEST_DATABASE_URL required")
        url = make_url(raw)
        if url.drivername != "postgresql+psycopg" or url.host not in {"127.0.0.1", "localhost", "::1"} or not (url.database or "").startswith("test_"):
            self.fail("Only a loopback test_* PostgreSQL database is allowed")
        self.schema = "auth_test_" + uuid4().hex
        self.engine = create_async_engine(url, poolclass=NullPool, connect_args={"options": "-csearch_path=" + self.schema})
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as conn:
            await conn.execute(text('CREATE SCHEMA "' + self.schema + '"'))
        self.addAsyncCleanup(self.clean_schema)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async def database():
            async with self.factory() as db:
                yield db
        app = FastAPI(); app.include_router(auth.router)
        app.dependency_overrides[auth.get_db] = database
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def clean_schema(self):
        self.assertTrue(self.schema.startswith("auth_test_"))
        self.assertEqual(len(self.schema), 42)
        async with self.engine.begin() as conn:
            await conn.execute(text('DROP SCHEMA "' + self.schema + '" CASCADE'))

    async def tables(self, serial=False):
        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE TABLE roles(id BIGINT PRIMARY KEY, name VARCHAR(50) NOT NULL UNIQUE)"))
            await conn.execute(text("INSERT INTO roles VALUES(1,'ADMIN'),(7,'USER')"))
            await conn.execute(text("CREATE TABLE account(id " + ("BIGSERIAL" if serial else "BIGINT") + " PRIMARY KEY, "
                "email VARCHAR(255) NOT NULL UNIQUE, username VARCHAR(255) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, "
                "role_id BIGINT REFERENCES roles(id), is_active BOOLEAN NOT NULL DEFAULT TRUE, locked_until TIMESTAMPTZ, "
                "created_by VARCHAR(100), updated_by VARCHAR(100), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())"))

    async def register(self, identity):
        return await self.client.post("/api/auth/register", json={"email": identity + "@example.com", "username": identity, "password": "SyntheticTest123"})

    async def test_legacy_pk_without_sequence_allocates_unique_ids_concurrently(self):
        await self.tables()
        results = await asyncio.gather(*(self.register("legacy_" + str(index)) for index in range(3)))
        self.assertEqual([r.status_code for r in results], [201, 201, 201], [r.text for r in results])
        self.assertEqual(len({r.json()["account_id"] for r in results}), 3)
        async with self.factory() as db:
            self.assertEqual((await db.execute(text("SELECT DISTINCT role_id FROM account"))).scalars().all(), [7])

    async def test_concurrent_duplicate_is_a_business_error_not_a_500(self):
        await self.tables()
        results = await asyncio.gather(self.register("duplicate"), self.register("duplicate"))
        self.assertEqual(sorted(r.status_code for r in results), [201, 400], [r.text for r in results])

    async def test_native_sequence_is_used_without_schema_changes(self):
        await self.tables(serial=True)
        results = await asyncio.gather(*(self.register("serial_" + str(index)) for index in range(3)))
        self.assertEqual([r.status_code for r in results], [201, 201, 201], [r.text for r in results])
        self.assertEqual({r.json()["account_id"] for r in results}, {"1", "2", "3"})
