import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from apps.backend.api.tour import get_db
from apps.backend.app import app
from apps.backend.services.heritage import HeritageDetail, HeritageService


def make_detail(**overrides) -> HeritageDetail:
    data = dict(
        slug="lang-tu-duc",
        locale="vi",
        title="Lăng Tự Đức",
        subtitle="Không gian di sản Huế",
        region="hue",
        location_label="Huế",
        description="Mô tả mẫu",
        hero_image_url="https://cdn.example.com/hero.jpg",
        revision=3,
        published_at=datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc),
        source_title="Nguồn mẫu",
        source_url="https://example.org/source",
        source_license="CC BY-SA",
        scene_available=True,
    )
    data.update(overrides)
    return HeritageDetail(**data)


async def _fake_db():
    yield None  # service đã bị mock nên không cần session thật


class HeritageDetailApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_db] = _fake_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_db, None)

    def _get(self, detail, url="/api/heritage/lang-tu-duc"):
        mock = AsyncMock(return_value=detail)
        with patch.object(HeritageService, "get_published_detail", new=mock):
            response = self.client.get(url)
        return response, mock

    def test_returns_landing_fields(self) -> None:
        response, mock = self._get(make_detail())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["title"], "Lăng Tự Đức")
        self.assertEqual(body["subtitle"], "Không gian di sản Huế")
        self.assertEqual(body["region"], "hue")
        self.assertEqual(body["hero_image_url"], "https://cdn.example.com/hero.jpg")
        self.assertTrue(body["scene_available"])
        self.assertEqual(body["published_at"], "2026-10-01T08:00:00+00:00")
        self.assertEqual(
            body["sources"],
            [{"title": "Nguồn mẫu", "url": "https://example.org/source", "license": "CC BY-SA"}],
        )
        mock.assert_awaited_once_with(slug="lang-tu-duc", locale="vi")

    def test_does_not_expose_scene_assets(self) -> None:
        response, _ = self._get(make_detail())

        forbidden = {
            "stops", "model_url", "narration_url",
            "ambient_audio_url", "default_camera_clip_url", "highlights",
        }
        self.assertTrue(forbidden.isdisjoint(response.json().keys()))

    def test_scene_not_available_still_returns_intro(self) -> None:
        response, _ = self._get(make_detail(scene_available=False))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["scene_available"])
        self.assertEqual(response.json()["title"], "Lăng Tự Đức")

    def test_missing_source_gives_empty_sources(self) -> None:
        response, _ = self._get(
            make_detail(source_title=None, source_url=None, source_license=None)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"], [])

    def test_unknown_or_unpublished_returns_404(self) -> None:
        response, _ = self._get(None, url="/api/heritage/khong-ton-tai")

        self.assertEqual(response.status_code, 404)

    def test_locale_is_forwarded_without_fallback(self) -> None:
        _, mock = self._get(
            make_detail(locale="en"), url="/api/heritage/lang-tu-duc?locale=en"
        )

        mock.assert_awaited_once_with(slug="lang-tu-duc", locale="en")


if __name__ == "__main__":
    unittest.main()