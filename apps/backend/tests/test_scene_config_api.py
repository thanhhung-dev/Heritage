"""Scene 3D persistence, viewer compatibility and asset/sky association checks."""
import unittest

from apps.backend.api.admin import scene_config
from apps.backend.core import security
from apps.backend.core.assets import configure_asset_policy
from apps.backend.tests import test_admin_scenes as fixtures


class SceneConfigApiTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.SceneApiTests.setUpClass.__func__)
    create_database = fixtures.SceneApiTests.create_database
    sql = fixtures.SceneApiTests.sql
    login = fixtures.SceneApiTests.login
    headers = staticmethod(fixtures.SceneApiTests.headers)
    url = fixtures.SceneApiTests.url
    create_scene = fixtures.SceneApiTests.create_scene

    def setUp(self):
        fixtures.SceneApiTests.setUp(self)
        configure_asset_policy()
        self.addCleanup(configure_asset_policy)
        self.app.include_router(scene_config.router)
        self.scene = self.create_scene()
        self.foreign = self.create_scene(heritage=2)
        self.config_url = f'/api/admin/scenes/{self.scene["id"]}/3d-config'
        self.sql("INSERT INTO model_asset(id,scene_id,file_url,format,lod_level) VALUES "
                 "(1,:scene,'models/camera.glb','glb',0),(2,:foreign,'models/foreign.glb','glb',0)",
                 {"scene": self.scene["id"], "foreign": self.foreign["id"]})
        self.sql("INSERT INTO sky_preset(id,name,turbidity,elevation) VALUES(1,'Day',2,45)")

    def test_save_get_update_reuses_existing_viewer_fields(self):
        body = {"camera": {"start_position": [1, 2, 3], "start_target": {"x": 0, "y": 0, "z": 0},
                           "path_url": "models/camera.glb", "instant_move": True},
                "sky_preset_id": 1, "model_asset_ids": [1]}
        response = self.client.put(self.config_url, json=body)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(self.client.get(self.config_url).json(), result)
        self.assertEqual(result["camera"]["start_position"], [1, 2, 3])
        self.assertEqual(result["camera"]["path_url"], "models/camera.glb")
        self.assertEqual(result["sky"]["name"], "Day")
        self.assertEqual(result["models"][0]["id"], 1)
        self.assertIn("mieCoefficient", result["sky"])
        updated = self.client.put(self.config_url, json={"camera": {"node_name": "Camera"}})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertIsNone(updated.json()["camera"]["start_position"])
        self.assertIsNone(updated.json()["sky"])
        self.assertEqual(len(updated.json()["models"]), 1)

    def test_assets_must_exist_and_belong_to_scene(self):
        for data in ({"camera": {}, "model_asset_ids": [999]}, {"camera": {}, "model_asset_ids": [2]},
                     {"camera": {"path_url": "models/foreign.glb"}},
                     {"camera": {"path_url": "models/missing.glb"}}, {"camera": {}, "sky_preset_id": 999}):
            response = self.client.put(self.config_url, json=data)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertIsNone(self.client.get(self.config_url).json()["camera"]["path_url"])
        self.assertEqual(self.sql("SELECT scene_id FROM model_asset WHERE id=2")[0][0], self.foreign["id"])

    def test_r2_url_round_trip_and_disallowed_host_write_is_rolled_back(self):
        configure_asset_policy("https://cdn.example", ("cdn.example",))
        result = self.client.put(self.config_url, json={"camera": {"path_url": "https://cdn.example/models/camera.glb"}})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.sql("SELECT camera_path_url FROM scene WHERE id=:id", {"id": self.scene["id"]})[0][0],
                         "models/camera.glb")
        self.sql("UPDATE model_asset SET file_url='https://other.example/x.glb' WHERE id=1")
        response = self.client.put(self.config_url, json={"camera": {"node_name": "Uncommitted"}})
        self.assertEqual(response.status_code, 422)
        self.assertIsNone(self.sql("SELECT camera_node_name FROM scene WHERE id=:id", {"id": self.scene["id"]})[0][0])

    def test_invalid_environment_presets_are_rejected_without_global_mutation(self):
        self.sql("UPDATE sky_preset SET elevation=100")
        response = self.client.put(self.config_url, json={"camera": {}, "sky_preset_id": 1})
        self.assertEqual(response.status_code, 422)
        self.assertIn("elevation", response.json()["detail"])
        self.assertEqual(self.sql("SELECT elevation FROM sky_preset WHERE id=1")[0][0], 100)

    def test_both_endpoints_require_admin_and_existing_scene(self):
        self.assertEqual(self.client.get("/api/admin/scenes/999/3d-config").status_code, 404)
        self.assertEqual(self.client.put("/api/admin/scenes/999/3d-config", json={"camera": {}}).status_code, 404)
        self.client.headers.pop("Authorization")
        self.assertEqual(self.client.get(self.config_url).status_code, 401)
        self.assertEqual(self.client.put(self.config_url, json={"camera": {}}).status_code, 401)
        self.client.headers.update(self.headers(security.create_access_token({"sub": "2", "role": "admin"})))
        self.assertEqual(self.client.get(self.config_url).status_code, 403)
        self.assertEqual(self.client.put(self.config_url, json={"camera": {}}).status_code, 403)
