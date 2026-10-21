"""
Unit tests for `UserProfileUpdate` avatar/banner URL validation
(apps.backend.schemas.user). Pure Pydantic model validation — no database or
network required, so this runs even when Postgres/Docker is unavailable.
"""

import unittest

from pydantic import ValidationError

from apps.backend.schemas.user import UserProfileUpdate


class ProfileAvatarBannerUrlValidationTests(unittest.TestCase):
    """GET/PUT /api/profile/me renders avatar_url/banner_url directly as
    <img src>/CSS background-image, so only http(s) URLs may be stored."""

    def test_accepts_https_avatar_url(self) -> None:
        payload = UserProfileUpdate(avatar_url="https://example.com/avatar.jpg")
        self.assertEqual(payload.avatar_url, "https://example.com/avatar.jpg")

    def test_accepts_http_banner_url(self) -> None:
        payload = UserProfileUpdate(banner_url="http://example.com/banner.png")
        self.assertEqual(payload.banner_url, "http://example.com/banner.png")

    def test_trims_whitespace(self) -> None:
        payload = UserProfileUpdate(avatar_url="  https://example.com/avatar.jpg  ")
        self.assertEqual(payload.avatar_url, "https://example.com/avatar.jpg")

    def test_empty_string_clears_field(self) -> None:
        payload = UserProfileUpdate(avatar_url="   ")
        self.assertIsNone(payload.avatar_url)

    def test_none_is_allowed(self) -> None:
        payload = UserProfileUpdate(avatar_url=None, banner_url=None)
        self.assertIsNone(payload.avatar_url)
        self.assertIsNone(payload.banner_url)

    def test_rejects_javascript_scheme(self) -> None:
        with self.assertRaises(ValidationError) as raised:
            UserProfileUpdate(avatar_url="javascript:alert(1)")
        self.assertIn("http:// or https://", str(raised.exception))

    def test_rejects_data_scheme(self) -> None:
        with self.assertRaises(ValidationError):
            UserProfileUpdate(banner_url="data:text/html,<script>alert(1)</script>")

    def test_rejects_scheme_without_host(self) -> None:
        with self.assertRaises(ValidationError):
            UserProfileUpdate(avatar_url="https://")

    def test_rejects_relative_path(self) -> None:
        with self.assertRaises(ValidationError):
            UserProfileUpdate(avatar_url="/local/avatar.jpg")

    def test_featured_badges_limit_still_enforced(self) -> None:
        """Regression guard: adding the URL validator must not break the
        pre-existing featured_badges <= 3 validation."""
        with self.assertRaises(ValidationError):
            UserProfileUpdate(featured_badges=["a", "b", "c", "d"])


if __name__ == "__main__":
    unittest.main()
