"""Admin auth HTTP contracts with real Argon2, JWTs and isolated SQLite storage."""
import asyncio
import os
import secrets
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.backend.api import auth
from apps.backend.api.admin import auth as admin_auth
from apps.backend.core import security
from apps.backend.models.revoked_token import RevokedToken
from apps.backend.services.token_revocation import token_digest


class AdminAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "Test-only-Admin-Password!42"
        cls.password_hash = security.hash_password(cls.password)

    def setUp(self):
        self.enterContext(patch.dict(os.environ, {
            "JWT_SECRET_KEY": secrets.token_urlsafe(48), "JWT_ISSUER": "", "JWT_AUDIENCE": "",
            "APP_ENVIRONMENT": "test", "CORS_ORIGINS": "",
        }))
        temp = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{Path(temp) / 'auth.db'}")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        asyncio.run(self.create_database())
        self.addCleanup(lambda: asyncio.run(self.engine.dispose()))

        async def database():
            async with self.factory() as session:
                yield session

        self.app = FastAPI()
        self.app.include_router(admin_auth.router)
        self.app.include_router(auth.router)
        self.app.dependency_overrides[security.get_auth_db] = database
        self.app.dependency_overrides[auth.get_db] = database
        self.client = self.enterContext(TestClient(self.app))

    async def create_database(self):
        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE TABLE roles (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"))
            await conn.execute(text("""CREATE TABLE account (
                id INTEGER PRIMARY KEY, email TEXT UNIQUE, username TEXT UNIQUE,
                password_hash TEXT, is_active BOOLEAN, locked_until TIMESTAMP, role_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT, updated_by TEXT
            )"""))
            await conn.execute(text("INSERT INTO roles VALUES (1, 'USER'), (2, 'ADMIN')"))
            await conn.execute(text("""INSERT INTO account
                (id, email, username, password_hash, is_active, role_id)
                VALUES (:id, :email, :username, :password_hash, 1, :role_id)"""), [
                {"id": 1, "email": "admin@example.com", "username": "admin", "password_hash": self.password_hash, "role_id": 2},
                {"id": 2, "email": "user@example.com", "username": "user", "password_hash": self.password_hash, "role_id": 1},
            ])
            await conn.run_sync(lambda sync: RevokedToken.__table__.create(sync))

    def sql(self, statement, params=None):
        async def execute():
            async with self.engine.begin() as conn:
                result = await conn.execute(text(statement), params or {})
                return result.fetchall() if result.returns_rows else None
        return asyncio.run(execute())

    def login(self, email="admin@example.com", password=None):
        return self.client.post("/api/admin/login", json={
            "email": email, "password": self.password if password is None else password,
        })

    @staticmethod
    def headers(token):
        return {"Authorization": f"Bearer {token}"}

    def test_admin_login_issues_unique_expiring_bearer_tokens(self):
        response = self.login("ADMIN@example.com")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(body["user"], {
            "account_id": "1", "email": "admin@example.com", "username": "admin", "role": "admin",
        })
        self.assertEqual(response.headers["cache-control"], "no-store")
        claims = security.decode_access_token(body["access_token"])
        self.assertEqual(claims["sub"], "1")
        self.assertEqual(claims["type"], "access")
        self.assertEqual(claims["exp"] - claims["iat"], 3600)
        self.assertNotIn("password", claims)
        self.assertNotIn("password_hash", claims)
        self.assertNotEqual(body["access_token"], self.login().json()["access_token"])

    def test_unknown_account_and_wrong_password_share_401(self):
        unknown = self.login("missing@example.com")
        incorrect = self.login(password="incorrect")
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(unknown.json(), incorrect.json())
        self.assertEqual(incorrect.status_code, 401)

    def test_login_validation(self):
        for body in ({}, {"email": "admin@example.com"}, {"email": "bad", "password": "test"},
                     {"email": "admin@example.com", "password": ""}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/api/admin/login", json=body).status_code, 422)

    def test_regular_user_cannot_log_into_admin(self):
        self.assertEqual(self.login("user@example.com").status_code, 403)
        self.assertEqual(self.login("user@example.com", "wrong").status_code, 401)

    def test_disabled_and_temporarily_locked_admins_cannot_login(self):
        self.sql("UPDATE account SET is_active = 0 WHERE id = 1")
        self.assertEqual(self.login().status_code, 401)
        self.sql("UPDATE account SET is_active = 1, locked_until = :until WHERE id = 1", {
            "until": datetime.now(timezone.utc) + timedelta(hours=1),
        })
        self.assertEqual(self.login().status_code, 401)
        self.sql("UPDATE account SET locked_until = :until WHERE id = 1", {
            "until": datetime.now(timezone.utc) - timedelta(hours=1),
        })
        self.assertEqual(self.login().status_code, 200)

    def test_corrupt_password_hash_does_not_raise_500(self):
        self.sql("UPDATE account SET password_hash = 'invalid-hash' WHERE id = 1")
        self.assertEqual(self.login().status_code, 401)

    def test_logout_is_idempotent_and_persists_only_digest(self):
        token = self.login().json()["access_token"]
        for _ in range(2):
            response = self.client.post("/api/admin/logout", headers=self.headers(token))
            self.assertEqual(response.status_code, 204, response.text)
            self.assertEqual(response.content, b"")
        rows = self.sql("SELECT token_hash, expires_at FROM revoked_access_token")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], token_digest(token))
        self.assertNotEqual(rows[0][0], token)

    def test_logout_requires_valid_admin_credential(self):
        self.assertEqual(self.client.post("/api/admin/logout").status_code, 401)
        self.assertEqual(self.client.post("/api/admin/logout", headers=self.headers("invalid")).status_code, 401)
        user_token = security.create_access_token({"sub": "2", "role": "admin"})
        self.assertEqual(self.client.post("/api/admin/logout", headers=self.headers(user_token)).status_code, 403)

    def test_existing_public_login_contract_is_preserved(self):
        response = self.client.post("/api/auth/login", json={"email": "user@example.com", "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["role"], "user")

    def test_reset_token_is_not_an_access_token(self):
        reset = security.create_password_reset_token("admin@example.com")
        self.assertEqual(security.verify_reset_password_token(reset), "admin@example.com")
        self.assertEqual(self.client.post("/api/admin/logout", headers=self.headers(reset)).status_code, 401)


if __name__ == "__main__":
    unittest.main()
