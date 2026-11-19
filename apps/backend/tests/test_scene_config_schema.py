import unittest

from pydantic import ValidationError

from apps.backend.schemas.scene_config import SceneConfigUpdate


class SceneConfigSchemaTests(unittest.TestCase):
    def test_viewer_vector_formats_are_supported(self):
        for position in ([1, 2, 3], {"x": 1, "y": 2, "z": 3}):
            config = SceneConfigUpdate(camera={"start_position": position, "start_target": [0, 0, 0]})
            self.assertFalse(config.camera.instant_move)

    def test_invalid_vectors_poses_and_unknown_fields(self):
        for camera in ({"start_position": [1, 2]}, {"start_position": [True, 2, 3], "start_target": [0, 0, 0]},
                       {"start_position": ["1", 2, 3], "start_target": [0, 0, 0]},
                       {"start_position": [float("inf"), 2, 3], "start_target": [0, 0, 0]},
                       {"start_position": [1000001, 2, 3], "start_target": [0, 0, 0]},
                       {"start_position": [1, 2, 3]},
                       {"start_position": [0, 0, 0], "start_target": {"x": 0, "y": 0, "z": 0}},
                       {"instant_move": "true"}, {"fov": 75}):
            with self.subTest(camera=camera), self.assertRaises(ValidationError):
                SceneConfigUpdate(camera=camera)

    def test_asset_paths_reject_traversal_credentials_and_executable_urls(self):
        for path in ("../private.glb", "/absolute.glb", "//evil.example/x.glb", "file:///private.glb",
                     "javascript:alert(1)", "https://user:password@example.com/x.glb", "models/%2e%2e/x.glb",
                     "models/%252e%252e/x.glb", "models/x.glb?token=secret", "models\\x.glb", "models/x.glb#part"):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                SceneConfigUpdate(camera={"path_url": path})
