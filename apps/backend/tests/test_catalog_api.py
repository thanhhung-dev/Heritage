import secrets
import os
import psycopg
from unittest.mock import patch

from anyio import CancelScope
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy import event
from sqlalchemy.engine import make_url

from apps.backend.api import admin_catalog, catalog
from apps.backend.core import security
from apps.backend.core.assets import configure_asset_policy
from apps.backend.models.admin import AccountRole, AdminAccount
from apps.backend.models.heritage_classification import CulturalContent
from apps.backend.services.classification_worker import run_next
from apps.backend.tests import catalog_postgres_support as fixtures


class CatalogApiTests(fixtures.CatalogPostgresFixture):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.enterContext(patch.object(security, "SECRET_KEY", secrets.token_urlsafe(48)))
        configure_asset_policy("https://cdn.example", ("cdn.example",))
        self.addCleanup(configure_asset_policy)
        async with self.engine.begin() as conn:
            await conn.run_sync(AccountRole.__table__.create)
            await conn.run_sync(AdminAccount.__table__.create)
            await conn.execute(text("INSERT INTO roles VALUES(1,'USER'),(2,'ADMIN')"))
            await conn.execute(text("""INSERT INTO account(id,email,username,password_hash,is_active,role_id)
                VALUES(1,'admin@example.com','admin','unused',true,2),
                      (2,'user@example.com','user','unused',true,1)"""))
        async def database():
            async with self.factory() as db:
                try:
                    yield db
                finally:
                    with CancelScope(shield=True):
                        await db.close()
        app = FastAPI()
        app.include_router(catalog.router, prefix="/api")
        app.include_router(admin_catalog.router, prefix="/api")
        app.dependency_overrides[catalog.get_db] = database
        self.client = self.enterContext(TestClient(app))
        self.admin = {"Authorization": "Bearer " + security.create_access_token({"sub": "1", "role": "admin"})}

    async def drain(self):
        while await run_next(self.factory):
            pass

    def create(self, title="Cổ vật thử nghiệm", kind="artifact", **values):
        result = self.client.post("/api/admin/catalog/contents", headers=self.admin, json={
            "slug": "item-" + secrets.token_hex(6), "title": title, "entity_type_hint": kind,
            "source_url": "https://example.org/reviewed-source", "card_image_url": "images/object.jpg",
            "publish_state": "published", **values})
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()

    async def test_correct_sections_exclude_incidental_festivals_museums_and_narrators(self):
        mountain = await self.heritage("Ngũ Hành Sơn", "Ngũ Hành Sơn là một danh thắng. Có lễ hội tại đây.")
        await self.heritage("Bảo tàng Đà Nẵng", "Lưu giữ nhiều cổ vật.")
        async with self.engine.begin() as conn:
            voice = await conn.scalar(text("INSERT INTO voice(name) VALUES('Narrator only') RETURNING id"))
            await conn.execute(text("INSERT INTO heritage_voice(heritage_id,voice_id) VALUES(:h,:v)"), {"h": mountain, "v": voice})
        await self.drain()
        result = self.client.get("/api/catalog/sections")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.headers["cache-control"], "no-store")
        for key in ("festivals_practices", "people_traditions", "artifact_collection", "artifacts_treasures", "featured"):
            self.assertEqual(result.json()[key]["items"], [])
        landscapes = self.client.get("/api/catalog/contents?category=scenic_landscape").json()["items"]
        self.assertEqual([row["title"] for row in landscapes], ["Ngũ Hành Sơn"])

    async def test_artifact_facts_own_detail_and_real_festival_relation(self):
        heritage_id = await self.heritage("Ngũ Hành Sơn", "Ngũ Hành Sơn là một danh thắng.")
        artifact = self.create(verified_metadata={"material": {"value": "Gốm", "source_url": "https://example.org/material"}})
        festival = self.create("Lễ hội thử nghiệm", "event")
        await self.drain()
        async with self.factory() as db:
            place_id = await db.scalar(select(CulturalContent.id).where(CulturalContent.source_heritage_id == heritage_id))
        linked = self.client.post(f'/api/admin/catalog/contents/{festival["id"]}/relations', headers=self.admin,
            json={"object_id": place_id, "relation_type": "held_at", "source_url": "https://example.org/festival-source"})
        self.assertEqual(linked.status_code, 201, linked.text)
        sections = self.client.get("/api/catalog/sections").json()
        self.assertEqual([row["title"] for row in sections["festivals_practices"]["items"]], ["Lễ hội thử nghiệm"])
        self.assertEqual([row["id"] for row in sections["artifact_collection"]["items"]], [artifact["id"]])
        card = sections["artifact_collection"]["items"][0]
        self.assertEqual(card["metadata"]["material"]["value"], "Gốm")
        detail = self.client.get("/api/catalog/contents/" + festival["slug"])
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["related_entities"][0]["content"]["title"], "Ngũ Hành Sơn")
        all_ids = [row["id"] for section in sections.values() for row in section["items"]]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    async def test_drafts_review_and_unsafe_media_are_not_homepage_cards(self):
        draft = self.create(publish_state="draft")
        unsafe = self.create(card_image_url="javascript:alert(1)")
        await self.drain()
        self.assertEqual(self.client.get("/api/catalog/contents/" + draft["slug"]).status_code, 404)
        self.assertEqual(self.client.get("/api/catalog/sections/artifact_collection").json()["items"], [])
        self.assertEqual(self.client.get("/api/catalog/contents/" + unsafe["slug"]).status_code, 200)

    async def test_pagination_manual_override_and_current_database_admin_guard(self):
        for title in ("Bảo tàng A", "Bảo tàng B", "Bảo tàng C"):
            await self.heritage(title)
        await self.drain()
        first = self.client.get("/api/catalog/contents?category=museum&limit=2").json()
        second = self.client.get(f'/api/catalog/contents?category=museum&limit=2&offset={first["next_offset"]}').json()
        self.assertEqual((len(first["items"]), len(second["items"])), (2, 1))
        content_id = first["items"][0]["id"]
        override = self.client.put(f"/api/admin/catalog/contents/{content_id}/classification", headers=self.admin,
            json={"expected_revision": 1, "entity_type": "place", "categories": ["museum", "architecture"],
                  "primary_category": "museum", "reasoning_summary": "Reviewed architecture evidence."})
        self.assertEqual(override.status_code, 200, override.text)
        self.assertTrue(override.json()["locked_by_admin"])
        forged_role = {"Authorization": "Bearer " + security.create_access_token({"sub": "2", "role": "admin"})}
        self.assertEqual(self.client.get("/api/admin/catalog/contents", headers=forged_role).status_code, 403)
        async with self.engine.begin() as conn:
            await conn.execute(text("UPDATE account SET is_active=false WHERE id=1"))
        self.assertEqual(self.client.get("/api/admin/catalog/contents", headers=self.admin).status_code, 401)

    async def test_featured_requires_editorial_opt_in_media_and_a_real_tour_reference(self):
        heritage_id = await self.heritage("Chùa kiểm thử")
        await self.drain()
        async with self.factory() as db:
            content_id = await db.scalar(select(CulturalContent.id))
        result = self.client.patch(f"/api/admin/catalog/contents/{content_id}", headers=self.admin,
            json={"expected_revision": 1, "is_featured": True})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.client.get("/api/catalog/sections/featured").json()["items"], [])
        async with self.engine.begin() as conn:
            scene_id = await conn.scalar(text("INSERT INTO scene(heritage_id,sequence,title) VALUES(:id,0,'Scene') RETURNING id"), {"id": heritage_id})
            await conn.execute(text("INSERT INTO model_asset(scene_id,file_url) VALUES(:id,'models/test.glb')"), {"id": scene_id})
        self.assertEqual(len(self.client.get("/api/catalog/sections/featured").json()["items"]), 1)
        async with self.factory() as db:
            source = (await db.execute(text("SELECT publish_state,card_image_url FROM heritage WHERE id=:id"), {"id": heritage_id})).one()
            self.assertEqual(tuple(source), ("published", "images/test.jpg"))

    async def test_medium_confidence_is_review_only_and_queries_do_not_grow_per_card(self):
        await self.heritage("Unknown subject")
        from apps.backend.services.heritage_classifier import Prediction
        await run_next(self.factory, classifier=lambda *args, **kwargs: Prediction(
            "place", ("museum",), "museum", 0.7, "Uncertain evidence", "semantic"))
        review = self.client.get("/api/admin/catalog/contents?status=review", headers=self.admin)
        self.assertEqual(len(review.json()["items"]), 1)
        self.assertEqual(self.client.get("/api/catalog/contents").json()["items"], [])
        for _ in range(12):
            self.create()
        await self.drain()
        statements = []
        def capture(_connection, _cursor, statement, _parameters, _context, _many):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)
        event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
        try:
            result = self.client.get("/api/catalog/sections?limit=8")
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", capture)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(len(result.json()["artifact_collection"]["items"]), 8)
        self.assertLessEqual(len(statements), 10)

    async def test_worker_commit_between_public_queries_cannot_mix_entity_and_category_snapshots(self):
        created = self.create()
        await self.drain()
        changed = []
        url = make_url(os.environ["CATALOG_TEST_DATABASE_URL"]).set(drivername="postgresql")
        def change_after_entity_read(_connection, _cursor, statement, _parameters, _context, _many):
            if not changed and statement.lstrip().startswith("SELECT heritage_classifications."):
                changed.append(True)
                with psycopg.connect(url.render_as_string(hide_password=False),
                                     options="-csearch_path=" + self.schema) as connection:
                    connection.execute("UPDATE heritage_content SET entity_type='event',entity_type_hint='event' WHERE id=%s", (created["id"],))
                    connection.execute("DELETE FROM heritage_classifications WHERE content_id=%s", (created["id"],))
                    connection.execute("""INSERT INTO heritage_classifications(content_id,category_key,is_primary,
                        confidence,classification_source,reasoning_summary)
                        VALUES(%s,'festival',true,1,'manual','Concurrent reviewed identity')""", (created["id"],))
                    connection.execute("UPDATE heritage_content SET classification_status='applied',classified_revision=input_revision WHERE id=%s", (created["id"],))
        event.listen(self.engine.sync_engine, "before_cursor_execute", change_after_entity_read)
        try:
            result = self.client.get("/api/catalog/sections")
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", change_after_entity_read)
        self.assertTrue(changed)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["artifact_collection"]["items"][0]["primary_category"], "artifact")
        next_response = self.client.get("/api/catalog/sections").json()
        self.assertEqual(next_response["artifact_collection"]["items"], [])
        self.assertEqual(next_response["festivals_practices"]["items"][0]["primary_category"], "festival")
