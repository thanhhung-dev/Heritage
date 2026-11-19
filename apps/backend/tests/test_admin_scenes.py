"""Scene contracts with actual SQL uniqueness, foreign keys and cascades."""
import asyncio
import unittest

from sqlalchemy import text

from apps.backend.api.admin import scenes
from apps.backend.core import security
from apps.backend.tests import test_admin_auth as fixtures


class SceneApiTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.AdminAuthTests.setUpClass.__func__)
    create_database = fixtures.AdminAuthTests.create_database
    sql = fixtures.AdminAuthTests.sql
    login = fixtures.AdminAuthTests.login
    headers = staticmethod(fixtures.AdminAuthTests.headers)

    def setUp(self):
        fixtures.AdminAuthTests.setUp(self)
        # SQLite JSON columns exercise bind/result conversion without requiring
        # PostgreSQL JSONB. Minimal parents preserve the real FK/order rules.
        async def create():
            async with self.engine.begin() as conn:
                for ddl in (
                    "CREATE TABLE heritage(id INTEGER PRIMARY KEY)",
                    "CREATE TABLE sky_preset(id INTEGER PRIMARY KEY, name TEXT, turbidity FLOAT, rayleigh FLOAT, "
                    "mie_coefficient FLOAT, mie_directional_g FLOAT, elevation FLOAT, azimuth FLOAT, exposure FLOAT, "
                    "cloud_coverage FLOAT, cloud_density FLOAT, stars FLOAT, light_settings JSON, "
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
                    "CREATE TABLE scene(id INTEGER PRIMARY KEY, heritage_id INTEGER NOT NULL REFERENCES heritage(id), "
                    "sequence INTEGER NOT NULL CHECK(sequence>=-1), title TEXT NOT NULL, description TEXT, "
                    "sky_preset_id INTEGER REFERENCES sky_preset(id), camera_node_name TEXT, cam_start_pos JSON, "
                    "cam_start_target JSON, cam_zoom_pos JSON, cam_zoom_target JSON, camera_path_url TEXT, "
                    "instant_move BOOLEAN NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                    "UNIQUE(heritage_id,sequence))",
                    "CREATE TABLE model_asset(id INTEGER PRIMARY KEY, scene_id INTEGER NOT NULL REFERENCES scene(id) "
                    "ON DELETE CASCADE, file_url TEXT, format TEXT DEFAULT 'glb', lod_level INTEGER DEFAULT 0, "
                    "compression TEXT, file_size_bytes INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
                    "INSERT INTO heritage VALUES (1),(2)",
                ):
                    await conn.execute(text(ddl))
        asyncio.run(create())
        # Every request connection enables SQLite's otherwise-disabled FKs.
        from sqlalchemy import event
        @event.listens_for(self.engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        self.app.include_router(scenes.router)
        self.client.headers.update(self.headers(self.login().json()["access_token"]))

    def url(self, heritage=1):
        return f"/api/admin/heritages/{heritage}/scenes"

    def create_scene(self, title="Scene", heritage=1, **fields):
        response = self.client.post(self.url(heritage), json={"title": title, **fields})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_crud_association_and_database_child_cascade(self):
        scene = self.create_scene(description="History")
        url = self.url() + f'/{scene["id"]}'
        self.assertEqual(scene["sequence"], 0)
        self.assertEqual(self.client.get(url).json(), scene)
        self.assertEqual(self.client.get(self.url(2) + f'/{scene["id"]}').status_code, 404)
        updated = self.client.patch(url, json={"title": "Updated", "description": None})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["title"], "Updated")
        self.sql("INSERT INTO model_asset(id,scene_id,file_url) VALUES(1,:scene,'models/history.glb')",
                 {"scene": scene["id"]})
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.sql("SELECT id FROM model_asset"), [])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(self.url(999), json={"title": "Missing"}).status_code, 404)

    def test_scene_validation_and_sequence_conflicts(self):
        self.create_scene(sequence=-1)
        self.assertEqual(self.client.post(self.url(), json={"title": "Duplicate", "sequence": -1}).status_code, 409)
        for body in ({"title": " "}, {"title": "x", "sequence": -2}, {"title": "x", "sequence": True},
                     {"title": "x", "heritage_id": 2}):
            self.assertEqual(self.client.post(self.url(), json=body).status_code, 422)
        scene = self.create_scene()
        for body in ({}, {"title": None}, {"sequence": 1}, {"heritage_id": 2}):
            self.assertEqual(self.client.patch(self.url() + f'/{scene["id"]}', json=body).status_code, 422)

    def test_reorder_swaps_unique_sequences_and_pins_overview(self):
        overview = self.create_scene(sequence=-1)
        first, second = self.create_scene("First"), self.create_scene("Second")
        original = [first["id"], second["id"]]
        response = self.client.patch(self.url() + "/order", json={
            "scene_ids": original[::-1], "expected_scene_ids": original,
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([s["id"] for s in response.json()["items"]], original[::-1])
        self.assertEqual([s["sequence"] for s in response.json()["items"]], [0, 1])
        self.assertEqual(self.client.get(self.url() + f'/{overview["id"]}').json()["sequence"], -1)
        stale = self.client.patch(self.url() + "/order", json={"scene_ids": original, "expected_scene_ids": original})
        self.assertEqual(stale.status_code, 409)

    def test_invalid_reorder_does_not_change_any_sequence(self):
        first, second = self.create_scene("First"), self.create_scene("Second")
        foreign = self.create_scene("Foreign", heritage=2)
        original = [first["id"], second["id"]]
        for ids in ([first["id"]], [first["id"], first["id"]], [first["id"], foreign["id"]], [first["id"], 999]):
            response = self.client.patch(self.url() + "/order", json={"scene_ids": ids, "expected_scene_ids": original})
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual([r["id"] for r in self.client.get(self.url()).json()["items"]], original)

    def test_scene_list_pagination(self):
        self.create_scene(sequence=-1)
        self.create_scene()
        first = self.client.get(self.url(), params={"limit": 1}).json()
        second = self.client.get(self.url(), params={"after_sequence": first["next_after_sequence"]}).json()
        self.assertEqual(first["next_after_sequence"], -1)
        self.assertEqual(len(second["items"]), 1)
        self.assertIsNone(second["next_after_sequence"])

    def test_failed_final_order_write_rolls_back_temporary_sequences(self):
        first, second = self.create_scene("First"), self.create_scene("Second")
        self.sql("CREATE TRIGGER reject_final_order BEFORE UPDATE OF sequence ON scene "
                 "WHEN OLD.id=" + str(first["id"]) + " AND NEW.sequence=1 "
                 "BEGIN SELECT RAISE(ABORT, 'test relationship conflict'); END")
        original = [first["id"], second["id"]]
        result = self.client.patch(self.url() + "/order", json={
            "scene_ids": original[::-1], "expected_scene_ids": original,
        })
        self.assertEqual(result.status_code, 409, result.text)
        unchanged = self.client.get(self.url()).json()["items"]
        self.assertEqual([row["id"] for row in unchanged], original)
        self.assertEqual([row["sequence"] for row in unchanged], [0, 1])

    def test_all_scene_operations_require_admin(self):
        operations = [("get", ""), ("post", ""), ("get", "/1"), ("patch", "/1"),
                      ("delete", "/1"), ("patch", "/order")]
        self.client.headers.pop("Authorization")
        for method, path in operations:
            self.assertEqual(getattr(self.client, method)(self.url() + path).status_code, 401)
        self.client.headers.update(self.headers(security.create_access_token({"sub": "2", "role": "admin"})))
        for method, path in operations:
            self.assertEqual(getattr(self.client, method)(self.url() + path).status_code, 403)
