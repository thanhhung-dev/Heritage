"""
Comprehensive unit and integration tests for User Profile, Personalization
Consent, and Gamification (badges/milestones) APIs.
Story: HER-118 / HER-167

Test Coverage:
- GET /api/profile/me - Retrieve user profile (real JWT auth)
- PUT /api/profile/me - Update user profile (new fields, handle uniqueness, featured_badges limit)
- GET /api/profile/consent - Retrieve consent settings
- PUT /api/profile/consent - Update consent settings
- GET /api/profile/badges - Badge catalogue merged with unlock state
- GET /api/profile/milestones - Milestone catalogue merged with completion state
- Unauthenticated requests are rejected with 401/403
- Input validation for profile updates

These tests register and log in a real account via /api/auth so the
fake-auth security hole (account_id hardcoded to 1) cannot regress.
"""

import asyncio
import os
import secrets
import sys
import unittest

from fastapi.testclient import TestClient

from apps.backend.app import app
from apps.backend.db.base import configure_database, dispose_database


class ProfileConsentAPITests(unittest.TestCase):
    """Test suite for User Profile, Personalization Consent, and Gamification APIs."""

    @classmethod
    def _create_test_tables(cls) -> None:
        """Ensure the Profile/Gamification tables exist for this test run.

        admin_account is NOT created/dropped here - it belongs to the auth
        feature and must already exist for the FK to be valid.
        """
        from apps.backend.db.base import AsyncSessionLocal
        from apps.backend.models import Base

        async def create_tables():
            async with AsyncSessionLocal() as session:
                await session.run_sync(
                    lambda sync_session: Base.metadata.create_all(
                        sync_session.get_bind(),
                        tables=[
                            Base.metadata.tables["user_profile"],
                            Base.metadata.tables["user_consent"],
                            Base.metadata.tables["badge_definition"],
                            Base.metadata.tables["user_badge"],
                            Base.metadata.tables["milestone_level_definition"],
                            Base.metadata.tables["milestone_task_definition"],
                            Base.metadata.tables["user_milestone_task"],
                        ],
                        checkfirst=True,
                    )
                )
                await session.commit()

        asyncio.run(create_tables())

    @classmethod
    def setUpClass(cls) -> None:
        """Set up database configuration and register a real test account once for all tests."""
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        database_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/heritagegraph")
        configure_database(database_url)

        cls._create_test_tables()

        client = TestClient(app, raise_server_exceptions=False)
        suffix = secrets.token_hex(6)
        cls.test_email = f"profile_test_{suffix}@example.com"
        cls.test_username = f"profile_test_{suffix}"
        cls.test_password = "StrongP@ssw0rd123"

        register_response = client.post(
            "/api/auth/register",
            json={"email": cls.test_email, "username": cls.test_username, "password": cls.test_password},
        )
        assert register_response.status_code == 201, register_response.text
        cls.account_id = register_response.json()["account_id"]

        login_response = client.post(
            "/api/auth/login",
            json={"username_or_email": cls.test_username, "password": cls.test_password},
        )
        assert login_response.status_code == 200, login_response.text
        cls.access_token = login_response.json()["access_token"]
        cls.auth_headers = {"Authorization": f"Bearer {cls.access_token}"}

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up database configuration after all tests."""
        asyncio.run(dispose_database())

    def setUp(self) -> None:
        """Set up test client before each test."""
        self.client = TestClient(app, raise_server_exceptions=False)

    # ---- GET /api/profile/me ----

    def test_get_profile_me_requires_auth(self) -> None:
        """GET /api/profile/me without a Bearer token must be rejected."""
        response = self.client.get("/api/profile/me")
        self.assertIn(response.status_code, (401, 403))

    def test_get_profile_me(self) -> None:
        """GET /api/profile/me returns 200 with the clean FE-facing profile shape."""
        response = self.client.get("/api/profile/me", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)

        self.assertNotIn("id", data)
        self.assertNotIn("account_id", data)

        for field in (
            "display_name", "handle", "avatar_url", "banner_url", "bio",
            "country", "city", "display_email", "joined_at", "socials",
            "total_hours", "level", "featured_badges", "show_activity_on_profile",
        ):
            self.assertIn(field, data)

        self.assertIsInstance(data["display_email"], bool)
        self.assertIsInstance(data["show_activity_on_profile"], bool)
        self.assertIsInstance(data["total_hours"], (int, float))

    # ---- PUT /api/profile/me ----

    def test_put_profile_me(self) -> None:
        """PUT /api/profile/me updates profile (including new fields) and persists."""
        payload = {
            "display_name": "Test User",
            "handle": f"test_handle_{secrets.token_hex(4)}",
            "avatar_url": "https://example.com/avatar.jpg",
            "banner_url": "https://example.com/banner.jpg",
            "bio": "Test biography for user profile",
            "country": "Vietnam",
            "city": "Da Nang",
            "display_email": True,
            "socials": {"instagram": "@test", "linkedin": None, "twitter": "@test"},
            "show_activity_on_profile": False,
        }

        response = self.client.put("/api/profile/me", json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["display_name"], payload["display_name"])
        self.assertEqual(data["handle"], payload["handle"])
        self.assertEqual(data["avatar_url"], payload["avatar_url"])
        self.assertEqual(data["banner_url"], payload["banner_url"])
        self.assertEqual(data["bio"], payload["bio"])
        self.assertEqual(data["country"], payload["country"])
        self.assertEqual(data["city"], payload["city"])
        self.assertEqual(data["display_email"], True)
        self.assertEqual(data["show_activity_on_profile"], False)
        self.assertEqual(data["socials"]["instagram"], "@test")

        get_response = self.client.get("/api/profile/me", headers=self.auth_headers)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["display_name"], payload["display_name"])

    def test_put_profile_me_duplicate_handle_rejected(self) -> None:
        """PUT /api/profile/me with a handle already used by another account returns 400."""
        other_client = TestClient(app, raise_server_exceptions=False)
        suffix = secrets.token_hex(6)
        other_email = f"profile_test_other_{suffix}@example.com"
        other_username = f"profile_test_other_{suffix}"
        other_password = "StrongP@ssw0rd123"

        register_response = other_client.post(
            "/api/auth/register",
            json={"email": other_email, "username": other_username, "password": other_password},
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = other_client.post(
            "/api/auth/login",
            json={"username_or_email": other_username, "password": other_password},
        )
        self.assertEqual(login_response.status_code, 200)
        other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        taken_handle = f"taken_handle_{secrets.token_hex(4)}"
        set_response = other_client.put("/api/profile/me", json={"handle": taken_handle}, headers=other_headers)
        self.assertEqual(set_response.status_code, 200)

        conflict_response = self.client.put("/api/profile/me", json={"handle": taken_handle}, headers=self.auth_headers)
        self.assertEqual(conflict_response.status_code, 400)
        self.assertIn("detail", conflict_response.json())

    def test_put_profile_me_featured_badges_limit(self) -> None:
        """PUT /api/profile/me rejects more than 3 featured_badges."""
        response = self.client.put(
            "/api/profile/me", json={"featured_badges": ["a", "b", "c", "d"]}, headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 422)

    def test_put_profile_me_validation_error(self) -> None:
        """PUT /api/profile/me returns 422 for invalid display_name values."""
        response_empty = self.client.put("/api/profile/me", json={"display_name": ""}, headers=self.auth_headers)
        self.assertEqual(response_empty.status_code, 422)
        self.assertIn("detail", response_empty.json())

        response_long = self.client.put(
            "/api/profile/me", json={"display_name": "A" * 51}, headers=self.auth_headers
        )
        self.assertEqual(response_long.status_code, 422)
        self.assertIn("detail", response_long.json())

        response_valid = self.client.put(
            "/api/profile/me", json={"display_name": "A" * 50}, headers=self.auth_headers
        )
        self.assertEqual(response_valid.status_code, 200)

    # ---- GET / PUT /api/profile/consent ----

    def test_get_consent_requires_auth(self) -> None:
        """GET /api/profile/consent without a Bearer token must be rejected."""
        response = self.client.get("/api/profile/consent")
        self.assertIn(response.status_code, (401, 403))

    def test_get_consent(self) -> None:
        """GET /api/profile/consent returns 200 with only analytics_opt_in (no leaked ids)."""
        response = self.client.get("/api/profile/consent", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)

        self.assertNotIn("id", data)
        self.assertNotIn("account_id", data)
        self.assertIn("analytics_opt_in", data)
        self.assertIsInstance(data["analytics_opt_in"], bool)

    def test_put_consent(self) -> None:
        """PUT /api/profile/consent toggles analytics_opt_in and persists."""
        response_true = self.client.put(
            "/api/profile/consent", json={"analytics_opt_in": True}, headers=self.auth_headers
        )
        self.assertEqual(response_true.status_code, 200)
        self.assertEqual(response_true.json()["analytics_opt_in"], True)

        get_response_true = self.client.get("/api/profile/consent", headers=self.auth_headers)
        self.assertEqual(get_response_true.json()["analytics_opt_in"], True)

        response_false = self.client.put(
            "/api/profile/consent", json={"analytics_opt_in": False}, headers=self.auth_headers
        )
        self.assertEqual(response_false.status_code, 200)
        self.assertEqual(response_false.json()["analytics_opt_in"], False)

    # ---- GET /api/profile/badges ----

    def test_get_badges_requires_auth(self) -> None:
        """GET /api/profile/badges without a Bearer token must be rejected."""
        response = self.client.get("/api/profile/badges")
        self.assertIn(response.status_code, (401, 403))

    def test_get_badges(self) -> None:
        """GET /api/profile/badges returns the full seeded catalogue with unlock state."""
        response = self.client.get("/api/profile/badges", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 13)

        badge = data[0]
        for field in ("id", "title", "description", "icon_key", "is_unlocked"):
            self.assertIn(field, badge)
        self.assertFalse(any(b["is_unlocked"] for b in data))

    # ---- GET /api/profile/milestones ----

    def test_get_milestones_requires_auth(self) -> None:
        """GET /api/profile/milestones without a Bearer token must be rejected."""
        response = self.client.get("/api/profile/milestones")
        self.assertIn(response.status_code, (401, 403))

    def test_get_milestones(self) -> None:
        """GET /api/profile/milestones returns the full seeded catalogue with task completion state."""
        response = self.client.get("/api/profile/milestones", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)

        first_level = data[0]
        for field in ("id", "level_name", "description", "is_unlocked", "tasks"):
            self.assertIn(field, first_level)
        self.assertIsInstance(first_level["tasks"], list)
        self.assertGreater(len(first_level["tasks"]), 0)
        for task in first_level["tasks"]:
            for field in ("id", "title", "is_completed"):
                self.assertIn(field, task)


if __name__ == "__main__":
    unittest.main()
