"""Actual PostgreSQL + production routers/DDL for Khoa's auth, scene and 3D flows.

Only runs with the explicit disposable database used by verify_rag_postgres.py.
No dependency override replaces a service: only the DB session is isolated.
"""
import asyncio
import os
from pathlib import Path
import secrets
import unittest
from unittest.mock import patch
from uuid import uuid4

from anyio import CancelScope
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from apps.backend.api import auth, heritage
from apps.backend.api.admin import accounts, auth as admin_auth, rag, scene_config, scenes
from apps.backend.core import security
from apps.backend.core.assets import configure_asset_policy
from apps.backend.models.revoked_token import RevokedToken
from apps.backend.services.account_status import update_account_status
from apps.backend.tests import test_sprint4_postgres as fixtures

ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(os.environ.get("SPRINT4_POSTGRES_TEST_URL"), "explicit disposable PostgreSQL required")
class Sprint4ApplicationPostgresTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(fixtures.Sprint4PostgresTests.setUpClass.__func__)
    drop_schema = fixtures.Sprint4PostgresTests.drop_schema

    async def asyncSetUp(self):
        url = make_url(os.environ["SPRINT4_POSTGRES_TEST_URL"])
        if (url.drivername != "postgresql+psycopg" or not url.database
                or not (url.database.startswith("test_") or url.database.endswith("_test"))):
            self.fail("Only an explicit postgresql+psycopg test_* or *_test database is permitted")
        self.schema = "sprint4_test_" + uuid4().hex
        self.engine = create_async_engine(url, poolclass=NullPool,
            connect_args={"options": f"-csearch_path={self.schema}"})
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addAsyncCleanup(self.drop_schema)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.password = secrets.token_urlsafe(24)
        password_hash = await asyncio.to_thread(security.hash_password, self.password)
        self.enterContext(patch.dict(os.environ, {"JWT_SECRET_KEY": secrets.token_urlsafe(48),
                                                 "JWT_ISSUER": "", "JWT_AUDIENCE": ""}))
        configure_asset_policy("https://cdn.example", ("cdn.example",))
        self.addCleanup(configure_asset_policy)
        async with self.engine.begin() as conn:
            # Execute repository scene/heritage DDL, including actual identity
            # sequences, unique constraints and every child cascade.
            await conn.exec_driver_sql((ROOT / "schema.sql").read_text(encoding="utf-8"))
            # Active identity schema from reset_local_identity.py; never invoke
            # that destructive application maintenance command in a test.
            await conn.execute(text("CREATE TABLE roles(id BIGINT PRIMARY KEY, name TEXT NOT NULL UNIQUE)"))
            await conn.execute(text("""CREATE TABLE account(
                id BIGINT PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
                username VARCHAR(255) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE, locked_until TIMESTAMPTZ,
                role_id BIGINT REFERENCES roles(id), created_by VARCHAR(100), updated_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP)"""))
            for name in ("2026-11-19_account_token_version.sql", "2026-11-19_rag_pipeline.sql"):
                await conn.exec_driver_sql((ROOT / "apps/backend/migrations" / name).read_text(encoding="utf-8"))
            await conn.run_sync(RevokedToken.__table__.create)
            await conn.execute(text("INSERT INTO roles VALUES(1,'USER'),(2,'ADMIN')"))
            await conn.execute(text("""INSERT INTO account(id,email,username,password_hash,role_id)
                VALUES(1,'admin@example.com','admin',:hash,2),(2,'user@example.com','user',:hash,1)"""),
                {"hash": password_hash})
            await conn.execute(text("""INSERT INTO heritage(slug,title,publish_state)
                VALUES('sprint4-test','Sprint 4 test','published'),('foreign-test','Foreign test','draft')"""))
            await conn.execute(text("INSERT INTO sky_preset(name,turbidity,elevation) VALUES('Day',2,45)"))

        async def database():
            async with self.factory() as session:
                try:
                    yield session
                finally:
                    with CancelScope(shield=True):
                        await session.close()

        self.app = FastAPI()
        for router in (admin_auth.router, accounts.router, rag.router, scenes.router, scene_config.router, auth.router):
            self.app.include_router(router)
        self.app.include_router(heritage.router, prefix="/api")
        for dependency in (security.get_auth_db, auth.get_db, heritage.get_db):
            self.app.dependency_overrides[dependency] = database
        self.client = self.enterContext(TestClient(self.app))
        result = self.client.post("/api/admin/login", json={"email": "admin@example.com", "password": self.password})
        self.assertEqual(result.status_code, 200, result.text)
        self.admin_headers = {"Authorization": "Bearer " + result.json()["access_token"]}
        self.client.headers.update(self.admin_headers)

    async def test_concurrent_deactivation_invalidates_sessions_once_and_reactivation_requires_login(self):
        result = self.client.post("/api/auth/login", json={"email": "user@example.com", "password": self.password})
        self.assertEqual(result.status_code, 200, result.text)
        old = {"Authorization": "Bearer " + result.json()["access_token"]}

        async def deactivate():
            async with self.factory() as db:
                return await update_account_status(db, 2, False)

        results = await asyncio.gather(deactivate(), deactivate())
        self.assertTrue(all(not result.is_active for result in results))
        async with self.factory() as db:
            self.assertEqual(await db.scalar(text("SELECT token_version FROM account WHERE id=2")), 1)
        self.assertEqual(self.client.get("/api/auth/me", headers=old).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={
            "email": "user@example.com", "password": self.password}).status_code, 403)
        self.assertEqual(self.client.patch("/api/admin/accounts/2/status", json={"is_active": True}).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=old).status_code, 401)
        fresh = self.client.post("/api/auth/login", json={"email": "user@example.com", "password": self.password})
        self.assertEqual(fresh.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers={
            "Authorization": "Bearer " + fresh.json()["access_token"]}).status_code, 200)
        self.assertEqual(self.client.post("/api/admin/logout").status_code, 204)
        self.assertEqual(self.client.post("/api/admin/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/admin/rag/pipelines").status_code, 401)

    async def test_scene_crud_order_3d_public_viewer_and_real_child_cascades(self):
        base = "/api/admin/heritages/1/scenes"
        overview = self.client.post(base, json={"title": "Overview", "sequence": -1})
        self.assertEqual(overview.status_code, 201, overview.text)
        created = [self.client.post(base, json={"title": name}) for name in ("First", "Second")]
        self.assertTrue(all(response.status_code == 201 for response in created), [r.text for r in created])
        first, second = [response.json()["id"] for response in created]
        config = f"/api/admin/scenes/{first}/3d-config"
        async with self.engine.begin() as conn:
            await conn.execute(text("INSERT INTO model_asset(scene_id,file_url) VALUES(:id,'models/camera.glb')"), {"id": first})
            await conn.execute(text("INSERT INTO interactive(scene_id,mode) VALUES(:id,'orbit')"), {"id": first})
            await conn.execute(text("INSERT INTO interactive_highlight(interactive_id,popup_text) VALUES(1,'Child')"))
        body = {"camera": {"start_position": [1, 2, 3], "start_target": {"x": 0, "y": 0, "z": 0},
                           "path_url": "https://cdn.example/models/camera.glb", "instant_move": True},
                "sky_preset_id": 1, "model_asset_ids": [1]}
        saved = self.client.put(config, json=body)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.client.get(config).json(), saved.json())
        async with self.factory() as db:
            row = (await db.execute(text("SELECT cam_start_pos,cam_start_target,camera_path_url FROM scene WHERE id=:id"),
                                    {"id": first})).one()
            self.assertEqual(tuple(row), ([1, 2, 3], {"x": 0, "y": 0, "z": 0}, "models/camera.glb"))
        self.assertEqual(self.client.put(config, json={"camera": {}, "model_asset_ids": [999]}).status_code, 422)
        self.assertEqual(self.client.get(config).json(), saved.json())
        public = self.client.get("/api/heritages/sprint4-test")
        self.assertEqual(public.status_code, 200, public.text)
        self.assertEqual(public.json()["scenes"][0]["camera"], saved.json()["camera"])
        self.assertEqual(public.json()["scenes"][0]["sky"], saved.json()["sky"])
        self.assertEqual(self.client.get(f"/api/admin/heritages/2/scenes/{first}").status_code, 404)
        order = {"scene_ids": [second, first], "expected_scene_ids": [first, second]}
        reordered = self.client.patch(base + "/order", json=order)
        self.assertEqual(reordered.status_code, 200, reordered.text)
        self.assertEqual([r["id"] for r in reordered.json()["items"]], [second, first])
        self.assertEqual(self.client.patch(base + "/order", json=order).status_code, 409)
        self.assertEqual(self.client.get(base + f'/{overview.json()["id"]}').json()["sequence"], -1)
        updated = self.client.patch(base + f"/{first}", json={"title": "Updated", "description": None})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["title"], "Updated")
        self.assertEqual(self.client.delete(base + f"/{first}").status_code, 204)
        self.assertEqual(self.client.get(config).status_code, 404)
        async with self.factory() as db:
            for table in ("model_asset", "interactive", "interactive_highlight"):
                self.assertEqual(await db.scalar(text(f"SELECT count(*) FROM {table}")), 0)
