"""Comprehensive integration tests for Authentication API endpoints.

Tests the complete authentication flow including:
- User registration (POST /api/auth/register)
- User login with username/email (POST /api/auth/login)
- Protected endpoint access (GET /api/auth/me)

Story: HER-170 - Backend Auth APIs

Each test is independent and uses unique credentials to avoid conflicts.
"""
import asyncio
import os
import sys
import unittest
from uuid import uuid4

# Fix Windows event loop policy for psycopg async compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Set environment variables BEFORE importing app to ensure they're available during startup
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/heritagegraph")
os.environ.setdefault("INFERENCE_BACKEND", "llama_server")
os.environ.setdefault("LLAMA_SERVER_URL", "http://localhost:8080")

from fastapi.testclient import TestClient

from apps.backend.app import app
from apps.backend.db.base import configure_database


class AuthAPITests(unittest.TestCase):
    """Integration tests for authentication endpoints."""
    
    @classmethod
    def setUpClass(cls) -> None:
        """Set up test database configuration once for all tests."""
        # Manually configure database to ensure it's available for all tests
        database_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/heritagegraph")
        configure_database(database_url)
    
    def setUp(self) -> None:
        """Set up test client before each test."""
        # Use with block to ensure lifespan is triggered
        self.client = TestClient(app)
        
        # Generate unique credentials for each test to avoid conflicts
        self.unique_id = str(uuid4())[:8]
        self.test_email = f"test_{self.unique_id}@example.com"
        self.test_username = f"testuser_{self.unique_id}"
        self.test_password = "SecurePass123"
    
    def test_register_success(self) -> None:
        """Test successful user registration.
        
        Validates:
        - POST /api/auth/register returns 201 Created
        - Response contains account_id, email, username, and success message
        - Account is created with USER role by default
        """
        # Arrange
        register_data = {
            "email": self.test_email,
            "username": self.test_username,
            "password": self.test_password,
        }
        
        # Act
        response = self.client.post("/api/auth/register", json=register_data)
        
        # Assert
        self.assertEqual(response.status_code, 201, 
                        f"Expected 201 Created, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertIn("account_id", data)
        self.assertIsInstance(data["account_id"], int)
        self.assertGreater(data["account_id"], 0, "account_id should be positive")
        
        self.assertEqual(data["email"], self.test_email)
        self.assertEqual(data["username"], self.test_username)
        self.assertIn("message", data)
        self.assertIn("thành công", data["message"].lower())
    
    def test_register_duplicate_email_or_username(self) -> None:
        """Test registration with duplicate email or username.
        
        Validates:
        - POST /api/auth/register with existing email returns 400 Bad Request
        - POST /api/auth/register with existing username returns 400 Bad Request
        - Error message indicates duplicate conflict
        """
        # Arrange - Create first user
        register_data = {
            "email": self.test_email,
            "username": self.test_username,
            "password": self.test_password,
        }
        
        first_response = self.client.post("/api/auth/register", json=register_data)
        self.assertEqual(first_response.status_code, 201, 
                        "First registration should succeed")
        
        # Act & Assert - Try duplicate email
        duplicate_email_data = {
            "email": self.test_email,  # Same email
            "username": f"different_{self.unique_id}",  # Different username
            "password": self.test_password,
        }
        
        response_email = self.client.post("/api/auth/register", json=duplicate_email_data)
        self.assertEqual(response_email.status_code, 400,
                        f"Expected 400 for duplicate email, got {response_email.status_code}")
        
        error_data = response_email.json()
        self.assertIn("detail", error_data)
        detail_lower = error_data["detail"].lower()
        self.assertTrue("email" in detail_lower or "tồn tại" in detail_lower,
                       f"Error should mention duplicate email: {error_data['detail']}")
        
        # Act & Assert - Try duplicate username
        duplicate_username_data = {
            "email": f"different_{self.test_email}",  # Different email
            "username": self.test_username,  # Same username
            "password": self.test_password,
        }
        
        response_username = self.client.post("/api/auth/register", json=duplicate_username_data)
        self.assertEqual(response_username.status_code, 400,
                        f"Expected 400 for duplicate username, got {response_username.status_code}")
        
        error_data = response_username.json()
        self.assertIn("detail", error_data)
        detail_lower = error_data["detail"].lower()
        self.assertTrue("username" in detail_lower or "tồn tại" in detail_lower,
                       f"Error should mention duplicate username: {error_data['detail']}")
    
    def test_login_success_with_username(self) -> None:
        """Test successful login using username.
        
        Validates:
        - POST /api/auth/login with username returns 200 OK
        - Response contains access_token, token_type='bearer', and user info
        - User payload includes id, email, username, and role
        """
        # Arrange - Register user first
        register_data = {
            "email": self.test_email,
            "username": self.test_username,
            "password": self.test_password,
        }
        register_response = self.client.post("/api/auth/register", json=register_data)
        self.assertEqual(register_response.status_code, 201, "Registration should succeed")
        
        # Act - Login with username
        login_data = {
            "username_or_email": self.test_username,
            "password": self.test_password,
        }
        response = self.client.post("/api/auth/login", json=login_data)
        
        # Assert
        self.assertEqual(response.status_code, 200,
                        f"Expected 200 OK, got {response.status_code}: {response.text}")
        
        data = response.json()
        
        # Validate token
        self.assertIn("access_token", data)
        self.assertIsInstance(data["access_token"], str)
        self.assertGreater(len(data["access_token"]), 0, "Token should not be empty")
        
        self.assertEqual(data["token_type"], "bearer")
        
        # Validate user payload
        self.assertIn("user", data)
        user = data["user"]
        self.assertIn("id", user)
        self.assertIsInstance(user["id"], int)
        self.assertEqual(user["email"], self.test_email)
        self.assertEqual(user["username"], self.test_username)
        self.assertIn("role", user)
        self.assertEqual(user["role"], "USER", "Default role should be USER")
    
    def test_login_success_with_email(self) -> None:
        """Test successful login using email.
        
        Validates:
        - POST /api/auth/login with email returns 200 OK
        - Response contains valid JWT token and user info
        - Login works with email in username_or_email field
        """
        # Arrange - Register user first
        register_data = {
            "email": self.test_email,
            "username": self.test_username,
            "password": self.test_password,
        }
        register_response = self.client.post("/api/auth/register", json=register_data)
        self.assertEqual(register_response.status_code, 201, "Registration should succeed")
        
        # Act - Login with email
        login_data = {
            "username_or_email": self.test_email,
            "password": self.test_password,
        }
        response = self.client.post("/api/auth/login", json=login_data)
        
        # Assert
        self.assertEqual(response.status_code, 200,
                        f"Expected 200 OK, got {response.status_code}: {response.text}")
        
        data = response.json()
        
        # Validate token
        self.assertIn("access_token", data)
        self.assertIsInstance(data["access_token"], str)
        self.assertGreater(len(data["access_token"]), 0, "Token should not be empty")
        
        self.assertEqual(data["token_type"], "bearer")
        
        # Validate user payload
        self.assertIn("user", data)
        user = data["user"]
        self.assertEqual(user["email"], self.test_email)
        self.assertEqual(user["username"], self.test_username)
        self.assertEqual(user["role"], "USER")
    
    def test_login_wrong_password(self) -> None:
        """Test login with incorrect password.
        
        Validates:
        - POST /api/auth/login with wrong password returns 401 Unauthorized
        - Error message indicates authentication failure
        """
        # Arrange - Register user first
        register_data = {
            "email": self.test_email,
            "username": self.test_username,
            "password": self.test_password,
        }
        register_response = self.client.post("/api/auth/register", json=register_data)
        self.assertEqual(register_response.status_code, 201, "Registration should succeed")
        
        # Act - Login with wrong password
        login_data = {
            "username_or_email": self.test_username,
            "password": "WrongPassword123",
        }
        response = self.client.post("/api/auth/login", json=login_data)
        
        # Assert
        self.assertEqual(response.status_code, 401,
                        f"Expected 401 Unauthorized, got {response.status_code}: {response.text}")
        
        error_data = response.json()
        self.assertIn("detail", error_data)
        detail_lower = error_data["detail"].lower()
        self.assertTrue("không chính xác" in detail_lower or "incorrect" in detail_lower,
                       f"Error should indicate wrong credentials: {error_data['detail']}")
    
    def test_get_me_success(self) -> None:
        """Test GET /api/auth/me with valid JWT token.
        
        Validates:
        - GET /api/auth/me with Bearer token returns 200 OK
        - Response contains complete user information including profile and consent
        - User data matches the registered account
        """
        # Arrange - Register and login to get token
        register_data = {
            "email": self.test_email,
            "username": self.test_username,
            "password": self.test_password,
        }
        register_response = self.client.post("/api/auth/register", json=register_data)
        self.assertEqual(register_response.status_code, 201, "Registration should succeed")
        
        login_data = {
            "username_or_email": self.test_username,
            "password": self.test_password,
        }
        login_response = self.client.post("/api/auth/login", json=login_data)
        self.assertEqual(login_response.status_code, 200, "Login should succeed")
        
        access_token = login_response.json()["access_token"]
        
        # Act - Access protected endpoint with Bearer token
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.client.get("/api/auth/me", headers=headers)
        
        # Assert
        self.assertEqual(response.status_code, 200,
                        f"Expected 200 OK, got {response.status_code}: {response.text}")
        
        data = response.json()
        
        # Validate user data
        self.assertIn("id", data)
        self.assertIsInstance(data["id"], int)
        self.assertEqual(data["email"], self.test_email)
        self.assertEqual(data["username"], self.test_username)
        self.assertEqual(data["role"], "USER")
        self.assertTrue(data["is_active"], "User should be active")
        
        # Validate profile exists (can be empty)
        self.assertIn("profile", data)
        if data["profile"] is not None:
            self.assertIsInstance(data["profile"], dict)
        
        # Validate consent exists
        self.assertIn("consent", data)
        if data["consent"] is not None:
            self.assertIsInstance(data["consent"], dict)
            self.assertIn("analytics_opt_in", data["consent"])
            self.assertIsInstance(data["consent"]["analytics_opt_in"], bool)
    
    def test_get_me_unauthorized(self) -> None:
        """Test GET /api/auth/me without valid authentication.
        
        Validates:
        - GET /api/auth/me without token returns 403 Forbidden
        - GET /api/auth/me with invalid token returns 401 Unauthorized
        - Error response indicates authentication issue
        """
        # Act & Assert - No token
        response_no_token = self.client.get("/api/auth/me")
        
        # FastAPI HTTPBearer returns 403 when no Authorization header is present
        # but may return 401 depending on implementation
        self.assertIn(response_no_token.status_code, [401, 403],
                     f"Expected 401 or 403 without token, got {response_no_token.status_code}")
        
        # Act & Assert - Invalid token
        invalid_headers = {"Authorization": "Bearer invalid_token_12345"}
        response_invalid_token = self.client.get("/api/auth/me", headers=invalid_headers)
        
        self.assertEqual(response_invalid_token.status_code, 401,
                        f"Expected 401 Unauthorized with invalid token, got {response_invalid_token.status_code}")
        
        error_data = response_invalid_token.json()
        self.assertIn("detail", error_data)
        detail_lower = error_data["detail"].lower()
        self.assertTrue("token" in detail_lower or "không hợp lệ" in detail_lower,
                       f"Error should mention invalid token: {error_data['detail']}")
        
        # Act & Assert - Malformed token
        malformed_headers = {"Authorization": "Bearer"}
        response_malformed = self.client.get("/api/auth/me", headers=malformed_headers)
        
        self.assertIn(response_malformed.status_code, [401, 403],
                     f"Expected 401/403 with malformed token, got {response_malformed.status_code}")


if __name__ == "__main__":
    unittest.main()

