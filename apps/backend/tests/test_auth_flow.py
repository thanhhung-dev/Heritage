"""Isolated auth HTTP regression tests: no application DB, SMTP or OAuth writes."""
import unittest
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from apps.backend.api import auth
from apps.backend.core import security
from apps.backend.models.admin import AccountRole, AdminAccount


class AuthFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.enterContext(patch.object(security, "SECRET_KEY", "synthetic-auth-test-private-key-1234567890"))
        self.engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as conn:
            await conn.run_sync(AccountRole.__table__.create)
            await conn.run_sync(AdminAccount.__table__.create)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.factory() as db:
            db.add_all([AccountRole(id=1, name="ADMIN"), AccountRole(id=7, name="USER")])
            await db.commit()
        async def database():
            async with self.factory() as db:
                yield db
        self.app = FastAPI()
        self.app.include_router(auth.router)
        self.app.dependency_overrides[auth.get_db] = database
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def register(self, **values):
        return await self.client.post("/api/auth/register", json={"email": "khoa@example.com", "username": "khoa_test", "password": "ValidPass123", **values})

    async def login(self, **values):
        return await self.client.post("/api/auth/login", json={"email": "khoa@example.com", "password": "ValidPass123", **values})

    async def test_registration_normalizes_identity_keeps_password_and_never_grants_admin(self):
        result = await self.register(email=" Khoa@Example.COM ", username=" khoa_test ", password=" ValidPass123 ", role="admin", role_id=1)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()["email"], "khoa@example.com")
        async with self.factory() as db:
            account = await db.get(AdminAccount, int(result.json()["account_id"]))
            self.assertEqual(account.role_id, 7)
            self.assertNotEqual(account.password_hash, " ValidPass123 ")
            self.assertTrue(security.verify_password(" ValidPass123 ", account.password_hash))
            self.assertFalse(security.verify_password("ValidPass123", account.password_hash))

    async def test_validation_matches_registration_policy_without_creating_rows(self):
        for values in [{"password": "1234567"}, {"password": "        "}, {"password": "x" * 1025},
                       {"email": "invalid"}, {"username": "  ab  "}, {"username": "a" * 51}, {"username": "___"}]:
            result = await self.register(**values)
            self.assertEqual(result.status_code, 422, str(values.keys()))
            self.assertIsInstance(result.json()["detail"], list)
        async with self.factory() as db:
            self.assertEqual((await db.execute(select(AdminAccount))).scalars().all(), [])

    async def test_duplicate_email_case_and_username_have_clear_errors(self):
        self.assertEqual((await self.register()).status_code, 201)
        email = await self.register(email="KHOA@example.com", username="another")
        self.assertEqual(email.status_code, 400)
        self.assertIn("email", email.json()["detail"])
        username = await self.register(email="other@example.com")
        self.assertEqual(username.status_code, 400)
        self.assertIn("username", username.json()["detail"])

    async def test_login_works_with_normalized_email_and_has_generic_bad_credentials(self):
        await self.register()
        result = await self.login(email=" KHOA@EXAMPLE.COM ")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["user"]["role"], "user")
        claims = security.decode_access_token(result.json()["access_token"])
        self.assertEqual(claims["sub"], result.json()["user"]["account_id"])
        bad = await self.login(password="wrong")
        missing = await self.login(email="missing@example.com")
        self.assertEqual(bad.status_code, 401)
        self.assertEqual(bad.json(), missing.json())
        self.assertEqual((await self.login(password="")).status_code, 422)

    async def test_legacy_passwords_are_not_rejected_by_registration_length_rules(self):
        await self.register()
        async with self.factory() as db:
            await db.execute(update(AdminAccount).values(password_hash=security.hash_password("old")))
            await db.commit()
        self.assertEqual((await self.login(password="old")).status_code, 200)

    async def test_inactive_and_temporarily_locked_accounts_cannot_log_in(self):
        await self.register()
        for changes in [{"is_active": False}, {"is_active": True, "locked_until": datetime.now(timezone.utc) + timedelta(hours=1)}]:
            async with self.factory() as db:
                await db.execute(update(AdminAccount).values(**changes))
                await db.commit()
            self.assertEqual((await self.login()).status_code, 403)
        async with self.factory() as db:
            await db.execute(update(AdminAccount).values(locked_until=datetime.now(timezone.utc) - timedelta(hours=1)))
            await db.commit()
        self.assertEqual((await self.login()).status_code, 200)

    async def test_invalid_hash_is_a_failed_login_instead_of_an_internal_error(self):
        await self.register()
        async with self.factory() as db:
            await db.execute(update(AdminAccount).values(password_hash="not-an-argon-hash"))
            await db.commit()
        self.assertEqual((await self.login()).status_code, 401)

    async def test_missing_user_role_and_signing_configuration_fail_closed(self):
        async with self.factory() as db:
            await db.execute(update(AccountRole).where(AccountRole.id == 7).values(name="EDITOR"))
            await db.commit()
        self.assertEqual((await self.register()).status_code, 503)
        async with self.factory() as db:
            await db.execute(update(AccountRole).where(AccountRole.id == 7).values(name="USER"))
            await db.commit()
        await self.register()
        with patch.object(security, "SECRET_KEY", "your-secret-key-change-this-in-production"):
            result = await self.login()
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("access_token", result.json())

    async def test_me_reads_current_role_and_rejects_locked_or_reset_sessions(self):
        await self.register()
        result = await self.login()
        token = result.json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        async with self.factory() as db:
            await db.execute(update(AdminAccount).values(role_id=1))
            await db.commit()
        self.assertEqual((await self.client.get("/api/auth/me", headers=headers)).json()["role"], "admin")
        reset = security.create_password_reset_token("khoa@example.com")
        self.assertEqual((await self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + reset})).status_code, 401)
        async with self.factory() as db:
            await db.execute(update(AdminAccount).values(is_active=False))
            await db.commit()
        self.assertEqual((await self.client.get("/api/auth/me", headers=headers)).status_code, 403)

    async def google(self, claims):
        provider = AsyncMock()
        provider.__aenter__.return_value = provider
        provider.get.return_value = httpx.Response(200, json=claims)
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "synthetic-client"}), patch.object(auth.httpx, "AsyncClient", return_value=provider):
            return await self.client.post("/api/auth/google", json={"id_token": "synthetic-test-token"})

    async def test_google_rejects_wrong_audience_and_string_false_verified_email(self):
        for claims in [{"aud": "other-client", "email_verified": "true"}, {"aud": "synthetic-client", "email_verified": "false"}]:
            result = await self.google({"email": "khoa@example.com", **claims})
            self.assertEqual(result.status_code, 401, result.text)

    async def test_google_accounts_use_user_role_and_current_lock_checks(self):
        claims = {"aud": "synthetic-client", "email_verified": "true", "email": "Khoa@Example.com"}
        result = await self.google(claims)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["user"]["role"], "user")
        async with self.factory() as db:
            await db.execute(update(AdminAccount).values(locked_until=datetime.now(timezone.utc) + timedelta(hours=1)))
            await db.commit()
        self.assertEqual((await self.google(claims)).status_code, 403)

    async def test_unconfigured_google_and_database_have_actionable_service_errors(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": ""}):
            result = await self.client.post("/api/auth/google", json={"id_token": "unused-test-token"})
        self.assertEqual(result.status_code, 503)
        unbound = FastAPI(); unbound.include_router(auth.router)
        with patch.object(auth, "AsyncSessionLocal", async_sessionmaker()):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=unbound), base_url="http://test") as client:
                result = await client.post("/api/auth/login", json={"email": "khoa@example.com", "password": "x"})
        self.assertEqual(result.status_code, 503)
