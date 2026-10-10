"""Contract, missing-asset and error tests for the Heritage public API.

Story 4 task 4.7. These tests exercise the router layer with a stubbed
HeritageService (fastapi dependency override), so they run without a
database. ORM mapping is covered by the seeded integration checks; here we
assert the API contracts:

* response shapes (homepage / content overview / scene detail)
* derived scene slugs (sequence -> s1, s2, ...)
* empty collections return ``[]`` while optional objects return ``null``
* the error envelope for missing heritage / missing scene / invalid scene key
* the R2 asset URL policy (task 4.6)
"""
from __future__ import annotations

import unittest
from datetime import date
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from apps.backend.api.heritage import get_service
from apps.backend.app import app
from apps.backend.core.assets import AssetUrlPolicy, configure_asset_policy
from apps.backend.core.config import (
    ConfigurationError,
    cors_origins,
    validate_startup_config,
)


VALID_ENV = {
    "DATABASE_URL": (
        "postgresql+psycopg://heritagegraph:test-password@localhost:5433/heritagegraph"
    ),
    "INFERENCE_BACKEND": "llama_server",
    "LLAMA_SERVER_URL": "http://localhost:8080",
    "LLAMA_SERVER_TIMEOUT": "30",
}


# ── Fake ORM rows (SimpleNamespace satisfies from_attributes schemas) ──────

def make_heritage(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 1,
        "slug": "chua-thien-mu",
        "title": "Chùa Thiên Mụ",
        "tagline": "Oldest pagoda on the Perfume River",
        "description": None,
        "region": "Huế, Việt Nam",
        "lat": 16.4535,
        "lng": 107.545,
        "duration_seconds": 1500,
        "launch_date": date(2026, 10, 6),
        "publish_state": "published",
        "publish_date": date(2026, 10, 6),
        "headline": None,
        "map_zoom": None,
        "hover_video_url": None,
        "community_made": False,
        "presented_by_logo_url": None,
        "display_map": True,
        "splash_image_url": None,
        "card_image_url": None,
        "language1": SimpleNamespace(code="vi", name="Vietnamese"),
        "language2": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_voice(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 1,
        "name": "Nguyen Minh Anh",
        "title": "Hue Heritage Guide",
        "bio": None,
        "headshot_url": None,
        "intro_video_url": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_scene(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 10,
        "sequence": 0,
        "title": "Tam Quan",
        "description": "Cổng tam quan",
        "camera_node_name": None,
        "cam_start_pos": [0.0, 1.5, 6.0],
        "cam_start_target": [0.0, 1.0, 0.0],
        "cam_zoom_pos": None,
        "cam_zoom_target": None,
        "instant_move": False,
        "sky_preset": None,
        "model_assets": [],
        "voice_clips": [],
        "media_items": [],
        "interactives": [],
        "scene_highlights": [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_sky_preset(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 7,
        "name": "midday",
        "turbidity": 10.0,
        "rayleigh": 2.0,
        "elevation": 45.0,
        "azimuth": 180.0,
        "exposure": 1.0,
        "light_settings": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_model_asset(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 100,
        "file_url": "https://cdn.example.com/scenes/s1/tam-quan.glb",
        "format": "glb",
        "lod_level": 0,
        "compression": None,
        "file_size_bytes": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_voice_clip(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 200,
        "video_url": None,
        "audio_url": None,
        "bubble_text": None,
        "sort_order": 0,
        "voice": make_voice(),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_media_item(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 300,
        "type": "image",
        "title": None,
        "caption": None,
        "asset_url": "https://cdn.example.com/media/s1/photo.jpg",
        "thumb_url": None,
        "credit": None,
        "sort_order": 0,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_interactive(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 400,
        "mode": "orbit",
        "cam_pos": None,
        "cam_target": None,
        "explore_area": None,
        "highlights": [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_interactive_highlight(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 500,
        "popup_title": "Chuông đồng",
        "popup_text": None,
        "media_url": None,
        "cam_pos": None,
        "cam_target": None,
        "lens_pos": None,
        "lens_rot": None,
        "lens_scale": None,
        "sort_order": 0,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_scene_highlight(**overrides: Any) -> SimpleNamespace:
    data: dict[str, Any] = {
        "id": 600,
        "model_url": "https://cdn.example.com/highlights/bell.glb",
        "position": [1.0, 1.0, 0.0],
        "rotation": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
        "animation_type": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_row(heritage: Any, scenes: Any, voices: Any = None, overview: Any = None) -> dict[str, Any]:
    if voices is None:
        voices = []
    return {
        "heritage": heritage,
        "voices": voices,
        "voice_length": len(voices),
        "overview": overview,
        "scenes": scenes,
    }


# ── Stub service ────────────────────────────────────────────────────────────

class FakeHeritageService:
    """Mirrors HeritageService using in-memory rows (no database)."""

    def __init__(self, rows):
        self._rows = rows

    async def list_published(self):
        return [
            {
                "heritage": row["heritage"],
                "voices": row["voices"],
                "voice_length": row["voice_length"],
            }
            for row in self._rows
        ]

    async def get_by_slug(self, slug):
        for row in self._rows:
            if row["heritage"].slug == slug:
                return row["heritage"]
        return None

    async def get_content_by_slug(self, slug):
        for row in self._rows:
            if row["heritage"].slug == slug:
                return row
        return None


# ── Test base ────────────────────────────────────────────────────────────────

class HeritageApiTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(app.dependency_overrides.pop, get_service, None)
        self.addCleanup(configure_asset_policy)

    def _install_service(self, rows) -> None:
        service = FakeHeritageService(rows)
        app.dependency_overrides[get_service] = lambda: service


# ── Homepage: GET /api/heritages ─────────────────────────────────────────────

class HomepageTests(HeritageApiTestBase):
    def test_homepage_lists_published_heritages(self) -> None:
        heritage = make_heritage(card_image_url="https://cdn.example.com/card.jpg")
        voice = make_voice(headshot_url="https://cdn.example.com/voice.jpg")
        self._install_service([make_row(heritage, scenes=[], voices=[voice])])

        response = self.client.get("/api/heritages")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload, list)
        self.assertEqual(len(payload), 1)

        item = payload[0]
        self.assertEqual(item["slug"], "chua-thien-mu")
        self.assertEqual(item["title"], "Chùa Thiên Mụ")
        self.assertEqual(item["publish_state"], "published")
        self.assertEqual(item["language1"]["code"], "vi")
        self.assertIsNone(item["language2"])

        # Computed voices field (Heritage -> Scene -> VoiceClip -> Voice).
        self.assertEqual(item["voice_length"], 1)
        self.assertEqual(item["voices"][0]["name"], "Nguyen Minh Anh")
        self.assertEqual(item["voices"][0]["headshot_url"], "https://cdn.example.com/voice.jpg")
        self.assertEqual(item["card_image_url"], "https://cdn.example.com/card.jpg")

    def test_homepage_returns_empty_list_when_nothing_published(self) -> None:
        self._install_service([])

        response = self.client.get("/api/heritages")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


# ── Content (full single-load): GET /api/heritages/{slug} ─────────────────────

class ContentUpdateTests(HeritageApiTestBase):
    def test_returns_heritage_and_derived_scene_slugs(self) -> None:
        scenes = [
            make_scene(id=10, sequence=0, title="Tam Quan"),
            make_scene(id=11, sequence=1, title="Tháp Phước Duyên"),
        ]
        self._install_service([make_row(make_heritage(), scenes)])

        response = self.client.get("/api/heritages/chua-thien-mu")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["heritage"]["slug"], "chua-thien-mu")
        self.assertIsNone(payload["overview"])
        self.assertEqual(len(payload["scenes"]), 2)
        self.assertEqual(payload["scenes"][0]["id"], 10)
        self.assertEqual(payload["scenes"][0]["slug"], "s1")
        self.assertEqual(payload["scenes"][0]["title"], "Tam Quan")
        self.assertEqual(payload["scenes"][0]["sequence"], 0)
        self.assertEqual(payload["scenes"][1]["slug"], "s2")
        self.assertEqual(payload["scenes"][1]["sequence"], 1)

    def test_overview_scene_is_sequence_minus_one(self) -> None:
        overview = make_scene(
            id=99,
            sequence=-1,
            title="Chùa Thiên Mụ",
            description="Giới thiệu toàn cảnh",
        )
        scenes = [
            make_scene(id=10, sequence=0, title="Tam Quan"),
            make_scene(id=11, sequence=1, title="Tháp Phước Duyên"),
        ]
        self._install_service([make_row(make_heritage(), scenes, overview=overview)])

        response = self.client.get("/api/heritages/chua-thien-mu")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["overview"]["id"], 99)
        self.assertEqual(payload["overview"]["sequence"], -1)
        self.assertEqual(payload["overview"]["title"], "Chùa Thiên Mụ")
        # Overview is NOT duplicated inside scenes.
        self.assertEqual(len(payload["scenes"]), 2)
        self.assertTrue(all(sc["sequence"] >= 0 for sc in payload["scenes"]))

    def test_404_for_unknown_heritage(self) -> None:
        self._install_service([])

        response = self.client.get("/api/heritages/khong-ton-tai")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "HERITAGE_NOT_FOUND",
                    "message": "Heritage 'khong-ton-tai' not found",
                }
            },
        )

    def test_heritage_without_scenes_returns_empty_list(self) -> None:
        self._install_service([make_row(make_heritage(), scenes=[])])

        response = self.client.get("/api/heritages/chua-thien-mu")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scenes"], [])


# ── Scene payload structure inside the full content payload ─────────────────

class ScenePayloadTests(HeritageApiTestBase):
    def _install_scene_row(self, scene=None, heritage=None) -> None:
        heritage = heritage if heritage is not None else make_heritage()
        scene = scene if scene is not None else make_scene()
        self._install_service([make_row(heritage, [scene])])

    def test_scene_carries_full_payload(self) -> None:
        scene = make_scene(
            sequence=0,
            sky_preset=make_sky_preset(),
            camera_node_name="Camera_Main",
            instant_move=True,
            model_assets=[
                make_model_asset(lod_level=0),
                make_model_asset(
                    id=101,
                    lod_level=1,
                    file_url="https://cdn.example.com/scenes/s1/tam-quan-lod1.glb",
                    compression="draco",
                ),
            ],
            voice_clips=[
                make_voice_clip(sort_order=1),
                make_voice_clip(id=201, sort_order=0, bubble_text="Welcome"),
            ],
            media_items=[
                make_media_item(sort_order=1),
                make_media_item(id=301, sort_order=0),
            ],
            interactives=[
                make_interactive(highlights=[make_interactive_highlight(sort_order=0)])
            ],
            scene_highlights=[make_scene_highlight()],
        )
        self._install_scene_row(scene)

        response = self.client.get("/api/heritages/chua-thien-mu")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["heritage"]["slug"], "chua-thien-mu")
        self.assertEqual(len(payload["scenes"]), 1)
        sc = payload["scenes"][0]
        self.assertEqual(
            (sc["id"], sc["slug"], sc["title"], sc["description"], sc["sequence"]),
            (10, "s1", "Tam Quan", "Cổng tam quan", 0),
        )

        # Camera is derived from scene columns, not a DB table.
        camera = sc["camera"]
        self.assertEqual(camera["node_name"], "Camera_Main")
        self.assertEqual(camera["start_position"], [0.0, 1.5, 6.0])
        self.assertEqual(camera["start_target"], [0.0, 1.0, 0.0])
        self.assertTrue(camera["instant_move"])

        # Sky preset.
        self.assertEqual(sc["sky"]["name"], "midday")
        self.assertEqual(sc["sky"]["turbidity"], 10.0)

        # Models keep the DB column name (file_url) and LOD list.
        self.assertEqual(len(sc["models"]), 2)
        self.assertEqual(
            sc["models"][0]["file_url"],
            "https://cdn.example.com/scenes/s1/tam-quan.glb",
        )
        self.assertEqual(sc["models"][0]["format"], "glb")
        self.assertEqual(sc["models"][1]["lod_level"], 1)
        self.assertEqual(sc["models"][1]["compression"], "draco")

        # Voice clips sorted by sort_order with nested voice.
        self.assertEqual(sc["voice_clips"][0]["bubble_text"], "Welcome")
        self.assertEqual(sc["voice_clips"][0]["voice"]["name"], "Nguyen Minh Anh")
        self.assertEqual(sc["voice_clips"][1]["sort_order"], 1)

        # Media sorted by sort_order.
        self.assertEqual(sc["media"][0]["id"], 301)
        self.assertEqual(sc["media"][1]["id"], 300)

        # Interactive with nested highlights.
        self.assertEqual(sc["interactive"][0]["mode"], "orbit")
        self.assertEqual(
            sc["interactive"][0]["highlights"][0]["popup_title"], "Chuông đồng"
        )

        # Scene highlights.
        self.assertEqual(
            sc["highlights"][0]["model_url"],
            "https://cdn.example.com/highlights/bell.glb",
        )

    def test_empty_collections_are_lists_not_null(self) -> None:
        self._install_scene_row()

        response = self.client.get("/api/heritages/chua-thien-mu")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        sc = payload["scenes"][0]
        for key in ("models", "voice_clips", "media", "interactive", "highlights"):
            with self.subTest(key=key):
                self.assertEqual(sc[key], [])

    def test_missing_sky_returns_null(self) -> None:
        self._install_scene_row(make_scene(sky_preset=None))

        response = self.client.get("/api/heritages/chua-thien-mu")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["scenes"][0]["sky"])

    def test_missing_asset_urls_stay_null(self) -> None:
        scene = make_scene(
            voice_clips=[make_voice_clip(video_url=None, audio_url=None)],
            interactives=[
                make_interactive(highlights=[make_interactive_highlight(media_url=None)])
            ],
        )
        self._install_scene_row(scene)

        response = self.client.get("/api/heritages/chua-thien-mu")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        sc = payload["scenes"][0]
        self.assertEqual(len(sc["voice_clips"]), 1)
        self.assertIsNone(sc["voice_clips"][0]["video_url"])
        self.assertIsNone(sc["voice_clips"][0]["audio_url"])
        self.assertIsNone(sc["interactive"][0]["highlights"][0]["media_url"])


# ── R2 asset URL policy (task 4.6) ───────────────────────────────────────────

class AssetUrlPolicyTests(unittest.TestCase):
    def test_absolute_urls_pass_through(self) -> None:
        policy = AssetUrlPolicy()
        url = "https://cdn.example.com/scenes/s1/tam-quan.glb"
        self.assertEqual(policy.resolve(url), url)

    def test_empty_and_null_resolve_to_none(self) -> None:
        policy = AssetUrlPolicy()
        self.assertIsNone(policy.resolve(None))
        self.assertIsNone(policy.resolve(""))

    def test_relative_keys_are_joined_with_base_url(self) -> None:
        policy = AssetUrlPolicy(base_url="https://assets.heritage.vn/")
        self.assertEqual(
            policy.resolve("scenes/s1/tam-quan.glb"),
            "https://assets.heritage.vn/scenes/s1/tam-quan.glb",
        )
        self.assertEqual(
            policy.resolve("/scenes/s1/tam-quan.glb"),
            "https://assets.heritage.vn/scenes/s1/tam-quan.glb",
        )

    def test_relative_keys_pass_through_without_base_url(self) -> None:
        policy = AssetUrlPolicy()
        self.assertEqual(policy.resolve("scenes/s1/tam-quan.glb"), "scenes/s1/tam-quan.glb")

    def test_allowlist_rejects_unknown_hosts(self) -> None:
        policy = AssetUrlPolicy(allowed_hosts=("assets.heritage.vn",))
        allowed = "https://assets.heritage.vn/a.glb"
        self.assertEqual(policy.resolve(allowed), allowed)
        self.assertIsNone(policy.resolve("https://evil.example.com/a.glb"))


class AssetUrlPolicyApiTests(HeritageApiTestBase):
    def test_api_resolves_relative_asset_urls_against_r2_base(self) -> None:
        configure_asset_policy(base_url="https://assets.heritage.vn")
        scene = make_scene(
            model_assets=[make_model_asset(file_url="scenes/s1/tam-quan.glb")],
            voice_clips=[
                make_voice_clip(
                    audio_url="voices/intro.mp3",
                    voice=make_voice(headshot_url="voices/face.jpg"),
                )
            ],
            media_items=[make_media_item(asset_url="media/photo.jpg")],
            interactives=[
                make_interactive(
                    highlights=[make_interactive_highlight(media_url="media/popup.mp4")]
                )
            ],
            scene_highlights=[make_scene_highlight(model_url="highlights/bell.glb")],
        )
        heritage = make_heritage(splash_image_url="heritage/splash.jpg")
        self._install_service([make_row(heritage, [scene])])

        response = self.client.get("/api/heritages/chua-thien-mu")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        heritage = payload["heritage"]
        scene = payload["scenes"][0]
        self.assertEqual(
            scene["models"][0]["file_url"],
            "https://assets.heritage.vn/scenes/s1/tam-quan.glb",
        )
        self.assertEqual(
            scene["voice_clips"][0]["audio_url"], "https://assets.heritage.vn/voices/intro.mp3"
        )
        self.assertEqual(
            scene["voice_clips"][0]["voice"]["headshot_url"],
            "https://assets.heritage.vn/voices/face.jpg",
        )
        self.assertEqual(
            scene["media"][0]["asset_url"], "https://assets.heritage.vn/media/photo.jpg"
        )
        self.assertEqual(
            scene["interactive"][0]["highlights"][0]["media_url"],
            "https://assets.heritage.vn/media/popup.mp4",
        )
        self.assertEqual(
            scene["highlights"][0]["model_url"],
            "https://assets.heritage.vn/highlights/bell.glb",
        )
        self.assertEqual(
            heritage["splash_image_url"],
            "https://assets.heritage.vn/heritage/splash.jpg",
        )


# ── R2 / CORS startup config ─────────────────────────────────────────────────

class R2StartupConfigTests(unittest.TestCase):
    def test_defaults_disable_r2_and_use_local_cors(self) -> None:
        settings = validate_startup_config(VALID_ENV)
        self.assertIsNone(settings.r2_public_base_url)
        self.assertEqual(settings.r2_allowed_asset_hosts, ())
        self.assertEqual(
            settings.cors_origins,
            ("http://localhost:3000", "http://127.0.0.1:3000"),
        )

    def test_r2_and_cors_values_are_normalized(self) -> None:
        settings = validate_startup_config(
            {
                **VALID_ENV,
                "R2_PUBLIC_BASE_URL": "https://assets.heritage.vn/",
                "R2_ALLOWED_ASSET_HOSTS": "Assets.Heritage.VN, cdn.example.com",
                "CORS_ORIGINS": "https://heritage.vn, https://www.heritage.vn",
            }
        )
        self.assertEqual(settings.r2_public_base_url, "https://assets.heritage.vn")
        self.assertEqual(
            settings.r2_allowed_asset_hosts, ("assets.heritage.vn", "cdn.example.com")
        )
        self.assertEqual(
            settings.cors_origins, ("https://heritage.vn", "https://www.heritage.vn")
        )

    def test_invalid_r2_and_cors_values_are_reported_together(self) -> None:
        with self.assertRaises(ConfigurationError) as raised:
            validate_startup_config(
                {
                    **VALID_ENV,
                    "R2_PUBLIC_BASE_URL": "not-a-url",
                    "R2_ALLOWED_ASSET_HOSTS": "https://bad.example.com/path",
                    "CORS_ORIGINS": "heritage.vn",
                }
            )
        message = str(raised.exception)
        self.assertIn("R2_PUBLIC_BASE_URL must be a valid", message)
        self.assertIn(
            "R2_ALLOWED_ASSET_HOSTS must be a comma-separated list of host names", message
        )
        self.assertIn("CORS_ORIGINS must be a comma-separated list of", message)

    def test_cors_origins_helper_reads_env(self) -> None:
        self.assertEqual(
            cors_origins({}),
            ["http://localhost:3000", "http://127.0.0.1:3000"],
        )
        self.assertEqual(
            cors_origins({"CORS_ORIGINS": "https://a.example.com, https://b.example.com"}),
            ["https://a.example.com", "https://b.example.com"],
        )


if __name__ == "__main__":
    unittest.main()
