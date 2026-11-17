"""Admin auth HTTP contracts with real Argon2, JWTs and isolated SQLite storage."""
import asyncio
import os
import secrets
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from apps.backend.api import admin_knowledge, auth
from apps.backend.api.admin import router as split_admin
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
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{Path(temp) / 'auth.db'}", poolclass=NullPool)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        asyncio.run(self.create_database())
        self.addCleanup(lambda: asyncio.run(self.engine.dispose()))

        async def database():
            async with self.factory() as session:
                yield session

        self.app = FastAPI()
        self.app.include_router(admin_auth.router)
        self.app.include_router(auth.router)
        self.app.include_router(admin_knowledge.router, prefix="/api")
        self.app.include_router(split_admin.router, prefix="/split")
        self.app.dependency_overrides[security.get_auth_db] = database
        self.app.dependency_overrides[auth.get_db] = database
        self.client = self.enterContext(TestClient(self.app))

        @self.app.get("/protected-admin")
        async def protected_admin(user=Depends(security.require_admin)):
            return {"account_id": user["sub"], "role": user["role"]}

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

    def test_admin_can_access_protected_endpoint(self):
        token = self.login().json()["access_token"]
        response = self.client.get("/protected-admin", headers=self.headers(token))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["role"], "admin")

    def test_missing_malformed_expired_and_bad_signature_return_401(self):
        invalid_tokens = [
            "garbage", "a.b.c",
            security.create_access_token({"sub": "1"}, timedelta(seconds=-1)),
            jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                       secrets.token_urlsafe(48), algorithm="HS256"),
            jwt.encode({"sub": "1"}, security.signing_key(), algorithm="HS256"),
            security.create_password_reset_token("admin@example.com"),
            jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(hours=1)}, security.signing_key(), algorithm="HS256"),
        ]
        for path in ("/protected-admin", "/api/auth/me"):
            self.assertEqual(self.client.get(path).status_code, 401)
            self.assertEqual(self.client.get(path, headers={"Authorization": "Basic abc"}).status_code, 401)
            for token in invalid_tokens:
                with self.subTest(path=path, token=token[:8]):
                    response = self.client.get(path, headers=self.headers(token))
                    self.assertEqual(response.status_code, 401, response.text)
                    self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_current_database_role_overrides_stale_or_forged_claim(self):
        forged_admin = security.create_access_token({"sub": "2", "role": "admin"})
        self.assertEqual(self.client.get("/protected-admin", headers=self.headers(forged_admin)).status_code, 403)
        admin = self.login().json()["access_token"]
        self.sql("UPDATE account SET role_id = 1 WHERE id = 1")
        self.assertEqual(self.client.get("/protected-admin", headers=self.headers(admin)).status_code, 403)

    def test_disabled_locked_deleted_or_invalid_account_cannot_access_admin(self):
        token = self.login().json()["access_token"]
        self.sql("UPDATE account SET is_active = 0 WHERE id = 1")
        self.assertEqual(self.client.get("/protected-admin", headers=self.headers(token)).status_code, 401)
        self.sql("UPDATE account SET is_active = 1, locked_until = :until WHERE id = 1", {
            "until": datetime.now(timezone.utc) + timedelta(hours=1),
        })
        self.assertEqual(self.client.get("/protected-admin", headers=self.headers(token)).status_code, 401)
        self.sql("DELETE FROM account WHERE id = 1")
        self.assertEqual(self.client.get("/protected-admin", headers=self.headers(token)).status_code, 401)
        for subject in ("not-an-id", "0", "-1", str(2**100)):
            invalid = security.create_access_token({"sub": subject, "role": "admin"})
            self.assertEqual(self.client.get("/protected-admin", headers=self.headers(invalid)).status_code, 401)

    def test_revocation_rejects_reuse_and_preserves_other_sessions(self):
        first = self.login().json()["access_token"]
        other = self.login().json()["access_token"]
        self.assertEqual(self.client.post("/api/admin/logout", headers=self.headers(first)).status_code, 204)
        for path in ("/protected-admin", "/api/auth/me", "/api/admin/storage/entries"):
            self.assertEqual(self.client.get(path, headers=self.headers(first)).status_code, 401)
        self.assertEqual(self.client.get("/protected-admin", headers=self.headers(other)).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.headers(other)).status_code, 200)
        # A fresh client shares the persistent database, not per-client memory.
        with TestClient(self.app) as fresh:
            self.assertEqual(fresh.get("/api/auth/me", headers=self.headers(first)).status_code, 401)

    def test_legacy_access_token_can_be_revoked(self):
        token = jwt.encode({
            "sub": "1", "role": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }, security.signing_key(), algorithm="HS256")
        self.assertEqual(self.client.get("/protected-admin", headers=self.headers(token)).status_code, 200)
        self.assertEqual(self.client.post("/api/admin/logout", headers=self.headers(token)).status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.headers(token)).status_code, 401)

    def test_every_admin_knowledge_route_enforces_authentication_and_role(self):
        regular = security.create_access_token({"sub": "2", "role": "user"})
        checked = {"/api/admin/": 0, "/split/admin/": 0}
        for path, operations in self.app.openapi()["paths"].items():
            prefix = next((value for value in checked if path.startswith(value)), None)
            if prefix is None or path in {"/api/admin/login", "/api/admin/logout"}:
                continue
            url = path.replace("{document_id}", "00000000-0000-0000-0000-000000000001")
            url = url.replace("{upload_id}", "00000000-0000-0000-0000-000000000001")
            for method, operation in operations.items():
                if method not in {"get", "post", "patch", "put", "delete"}:
                    continue
                with self.subTest(path=path, method=method):
                    self.assertTrue(operation["security"])
                    self.assertEqual(self.client.request(method, url).status_code, 401)
                    self.assertEqual(self.client.request(method, url, headers=self.headers(regular)).status_code, 403)
                checked[prefix] += 1
        self.assertTrue(all(count >= 10 for count in checked.values()), checked)

    def test_login_then_real_knowledge_route_then_logout(self):
        token = self.login().json()["access_token"]
        self.app.dependency_overrides[admin_knowledge.get_storage] = lambda: SimpleNamespace(
            entries=lambda *args: {"entries": [], "next_cursor": None},
        )
        with TestClient(self.app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)) as loopback:
            path = "/api/admin/storage/entries"
            self.assertEqual(loopback.get(path, headers=self.headers(token)).status_code, 200)
            self.assertEqual(loopback.post("/api/admin/logout", headers=self.headers(token)).status_code, 204)
            self.assertEqual(loopback.get(path, headers=self.headers(token)).status_code, 401)

    def test_configured_issuer_and_audience_are_validated(self):
        with patch.dict(os.environ, {"JWT_ISSUER": "heritage", "JWT_AUDIENCE": "heritage-admin"}):
            token = self.login().json()["access_token"]
            self.assertEqual(self.client.get("/protected-admin", headers=self.headers(token)).status_code, 200)
            for claim in ("iss", "aud"):
                payload = security.decode_access_token(token)
                payload[claim] = "incorrect"
                invalid = jwt.encode(payload, security.signing_key(), algorithm="HS256")
                self.assertEqual(self.client.get("/protected-admin", headers=self.headers(invalid)).status_code, 401)

    def test_missing_key_fails_closed_without_fallback(self):
        for key in ("", "your-secret-key-change-this-in-production"):
            with patch.dict(os.environ, {"JWT_SECRET_KEY": key}):
                response = self.login()
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(self.password, response.text)

    def test_database_unavailable_returns_503_but_bad_credentials_still_401(self):
        self.app.dependency_overrides.pop(security.get_auth_db)
        with patch.dict(security.AsyncSessionLocal.kw, {"bind": None}):
            self.assertEqual(self.login().status_code, 503)
            self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
            self.assertEqual(self.client.get("/api/auth/me", headers=self.headers("invalid")).status_code, 401)

    def test_database_errors_fail_closed_without_internal_details(self):
        token = self.login().json()["access_token"]
        self.sql("DROP TABLE revoked_access_token")
        self.app.dependency_overrides.pop(security.get_auth_db)
        with patch.object(security, "AsyncSessionLocal", self.factory):
            response = self.client.get("/api/auth/me", headers=self.headers(token))
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("SELECT", response.text)
            self.assertNotIn(token, response.text)

    def test_openapi_declares_admin_contract_and_actual_app_mounts_routes(self):
        from apps.backend.app import app
        paths = app.openapi()["paths"]
        self.assertIn("/api/admin/login", paths)
        self.assertIn("/api/admin/logout", paths)
        self.assertIn("/api/admin/storage/entries", paths)
        self.assertIn("204", paths["/api/admin/logout"]["post"]["responses"])
        self.assertTrue(paths["/api/admin/logout"]["post"]["security"])


if __name__ == "__main__":
    unittest.main()
