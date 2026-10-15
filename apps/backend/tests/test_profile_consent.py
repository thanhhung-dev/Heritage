"""
Comprehensive unit and integration tests for User Profile and Personalization Consent APIs.
Story: HER-118, Subtask: HER-168

Test Coverage:
- GET /api/profile/me - Retrieve user profile
- PUT /api/profile/me - Update user profile
- GET /api/profile/consent - Retrieve consent settings
- PUT /api/profile/consent - Update consent settings
- Input validation for profile updates
"""

import asyncio
import os
import sys
import unittest
from fastapi.testclient import TestClient

from apps.backend.app import app
from apps.backend.db.base import configure_database, dispose_database


class ProfileConsentAPITests(unittest.TestCase):
    """Test suite for User Profile and Personalization Consent APIs."""

    @classmethod
    def _create_test_tables(cls) -> None:
        """Create test database tables (user_profile and user_consent)."""
        import asyncio
        from sqlalchemy import text
        from apps.backend.db.base import AsyncSessionLocal
        
        async def create_tables():
            async with AsyncSessionLocal() as session:
                # Drop old tables if they exist (cleanup from previous test runs)
                await session.execute(text("DROP TABLE IF EXISTS user_profiles CASCADE"))
                await session.execute(text("DROP TABLE IF EXISTS user_consents CASCADE"))
                await session.execute(text("DROP TABLE IF EXISTS user_profile CASCADE"))
                await session.execute(text("DROP TABLE IF EXISTS user_consent CASCADE"))
                
                # Create user_profile table
                await session.execute(text("""
                    CREATE TABLE user_profile (
                        id SERIAL PRIMARY KEY,
                        account_id INTEGER UNIQUE NOT NULL,
                        display_name VARCHAR(255),
                        avatar_url TEXT,
                        bio TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                """))
                
                # Create user_consent table
                await session.execute(text("""
                    CREATE TABLE user_consent (
                        id SERIAL PRIMARY KEY,
                        account_id INTEGER UNIQUE NOT NULL,
                        analytics_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                """))
                
                # Create indexes
                await session.execute(text("""
                    CREATE INDEX idx_user_profile_account_id 
                    ON user_profile(account_id)
                """))
                
                await session.execute(text("""
                    CREATE INDEX idx_user_consent_account_id 
                    ON user_consent(account_id)
                """))
                
                await session.commit()
        
        asyncio.run(create_tables())

    @classmethod
    def setUpClass(cls) -> None:
        """Set up database configuration once for all tests."""
        # Fix Windows asyncio event loop compatibility with psycopg
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        database_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/heritagegraph")
        configure_database(database_url)
        
        # Create tables if they don't exist
        cls._create_test_tables()

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up database configuration after all tests."""
        import asyncio
        asyncio.run(dispose_database())

    def setUp(self) -> None:
        """Set up test client before each test."""
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_get_profile_me(self) -> None:
        """
        Test GET /api/profile/me returns 200 OK with valid UserProfileResponse JSON.
        
        Verifies:
        - Status code is 200
        - Response contains required fields: id, account_id, display_name, avatar_url, bio
        - Response structure matches UserProfileResponse schema
        """
        response = self.client.get("/api/profile/me")
        
        # Assert HTTP 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Assert valid JSON response
        data = response.json()
        self.assertIsInstance(data, dict)
        
        # Assert UserProfileResponse schema fields
        self.assertIn("id", data)
        self.assertIn("account_id", data)
        self.assertIn("display_name", data)
        self.assertIn("avatar_url", data)
        self.assertIn("bio", data)
        
        # Assert types
        self.assertIsInstance(data["id"], int)
        self.assertIsInstance(data["account_id"], int)
        self.assertEqual(data["account_id"], 1)  # Mock auth returns account_id=1

    def test_put_profile_me(self) -> None:
        """
        Test PUT /api/profile/me updates profile and returns 200 OK.
        
        Verifies:
        - Status code is 200
        - Profile fields are updated correctly (display_name, avatar_url, bio)
        - Response contains updated values
        """
        payload = {
            "display_name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg",
            "bio": "Test biography for user profile"
        }
        
        response = self.client.put("/api/profile/me", json=payload)
        
        # Assert HTTP 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Assert response contains updated data
        data = response.json()
        self.assertEqual(data["display_name"], payload["display_name"])
        self.assertEqual(data["avatar_url"], payload["avatar_url"])
        self.assertEqual(data["bio"], payload["bio"])
        
        # Verify persistence - GET should return updated values
        get_response = self.client.get("/api/profile/me")
        self.assertEqual(get_response.status_code, 200)
        get_data = get_response.json()
        self.assertEqual(get_data["display_name"], payload["display_name"])

    def test_get_consent(self) -> None:
        """
        Test GET /api/profile/consent returns 200 OK with boolean analytics_opt_in.
        
        Verifies:
        - Status code is 200
        - Response contains required fields: id, account_id, analytics_opt_in
        - analytics_opt_in is a boolean value
        """
        response = self.client.get("/api/profile/consent")
        
        # Assert HTTP 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Assert valid JSON response
        data = response.json()
        self.assertIsInstance(data, dict)
        
        # Assert UserConsentResponse schema fields
        self.assertIn("id", data)
        self.assertIn("account_id", data)
        self.assertIn("analytics_opt_in", data)
        
        # Assert types
        self.assertIsInstance(data["id"], int)
        self.assertIsInstance(data["account_id"], int)
        self.assertIsInstance(data["analytics_opt_in"], bool)
        self.assertEqual(data["account_id"], 1)

    def test_put_consent(self) -> None:
        """
        Test PUT /api/profile/consent toggles analytics_opt_in and returns 200 OK.
        
        Verifies:
        - Status code is 200
        - analytics_opt_in can be toggled to True
        - analytics_opt_in can be toggled back to False
        - Changes persist correctly
        """
        # Test setting consent to True
        payload_true = {"analytics_opt_in": True}
        response_true = self.client.put("/api/profile/consent", json=payload_true)
        
        # Assert HTTP 200 OK
        self.assertEqual(response_true.status_code, 200)
        
        # Assert consent is now True
        data_true = response_true.json()
        self.assertEqual(data_true["analytics_opt_in"], True)
        
        # Verify persistence - GET should return True
        get_response_true = self.client.get("/api/profile/consent")
        self.assertEqual(get_response_true.status_code, 200)
        self.assertEqual(get_response_true.json()["analytics_opt_in"], True)
        
        # Test toggling consent to False
        payload_false = {"analytics_opt_in": False}
        response_false = self.client.put("/api/profile/consent", json=payload_false)
        
        # Assert HTTP 200 OK
        self.assertEqual(response_false.status_code, 200)
        
        # Assert consent is now False
        data_false = response_false.json()
        self.assertEqual(data_false["analytics_opt_in"], False)

    def test_put_profile_me_validation_error(self) -> None:
        """
        Test PUT /api/profile/me returns 422 for invalid data.
        
        Verifies:
        - Empty display_name returns 422
        - display_name longer than 50 characters returns 422
        - Response contains validation error details
        """
        # Test Case 1: Empty display_name
        payload_empty = {"display_name": ""}
        response_empty = self.client.put("/api/profile/me", json=payload_empty)
        
        # Assert HTTP 422
        self.assertEqual(response_empty.status_code, 422)
        error_data = response_empty.json()
        self.assertIn("detail", error_data)
        
        # Test Case 2: display_name exceeds max_length=50
        payload_long = {"display_name": "A" * 51}
        response_long = self.client.put("/api/profile/me", json=payload_long)
        
        # Assert HTTP 422
        self.assertEqual(response_long.status_code, 422)
        error_data_long = response_long.json()
        self.assertIn("detail", error_data_long)
        
        # Verify valid boundary (50 chars) works
        payload_valid = {"display_name": "A" * 50}
        response_valid = self.client.put("/api/profile/me", json=payload_valid)
        self.assertEqual(response_valid.status_code, 200)


if __name__ == "__main__":
    unittest.main()
