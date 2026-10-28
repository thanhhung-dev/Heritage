"""Registration regression tests with real ORM flushes, Argon2 and JWTs.

Only the async database adapter is replaced, using a disposable SQLite database.
No local accounts, SMTP service, LLM or database configuration are required.
"""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

from apps.backend.api import auth as auth_api
from apps.backend.core.security import verify_password
from apps.backend.models.admin import AccountRole, AdminAccount
from apps.backend.services.accounts import AccountService


class AsyncAuthSession:
    """Use the real transactional ORM without an additional async test driver."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, entity):
        self.session.add(entity)

    async def execute(self, statement, params=None):
        return self.session.execute(statement, params)

    async def commit(self):
        self.session.commit()

    async def flush(self):
        self.session.flush()

    async def rollback(self):
        self.session.rollback()

    async def refresh(self, entity):
        self.session.refresh(entity)


class AuthAPITests(unittest.TestCase):
    def setUp(self):
        metadata = MetaData()
        AccountRole.__table__.to_metadata(metadata)
        AdminAccount.__table__.to_metadata(metadata)
        self.engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False},
        )
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        # Schema creation is restricted to this disposable in-memory database.
        metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(metadata.tables["roles"].insert(), [
                {"id": 1, "name": "USER"}, {"id": 2, "name": "ADMIN"},
            ])

        async def get_db():
            with Session(self.engine, expire_on_commit=False) as session:
                yield AsyncAuthSession(session)

        app = FastAPI()
        app.include_router(auth_api.router)
        app.dependency_overrides[auth_api.get_db] = get_db
        self.client = self.enterContext(TestClient(app))
        self.registration = {
            "email": "registration@example.com", "username": "registration_test",
            "password": "RegistrationTest@2026",
        }

    def register(self, **changes):
        return self.client.post("/api/auth/register", json={**self.registration, **changes})

    def count_accounts(self):
        with Session(self.engine) as session:
            return session.scalar(select(func.count()).select_from(AdminAccount))

    def test_role_foreign_key_resolves_to_the_registered_role_model(self):
        # Missing roles metadata caused NoReferencedTableError on ORM flush,
        # even though the physical PostgreSQL table already existed.
        foreign_key = next(iter(AdminAccount.__table__.c.role_id.foreign_keys))
        self.assertIs(foreign_key.column, AccountRole.__table__.c.id)

    def test_register_creates_hashed_user_account_with_timestamps(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertEqual(data["email"], self.registration["email"])
        self.assertEqual(data["username"], self.registration["username"])
        self.assertIsInstance(data["account_id"], str)
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)
        with Session(self.engine) as session:
            account = session.get(AdminAccount, int(data["account_id"]))
            self.assertIsNotNone(account)
            self.assertEqual(account.role_id, 1)
            self.assertTrue(account.is_active)
            self.assertIsNotNone(account.created_at)
            self.assertIsNotNone(account.updated_at)
            self.assertNotEqual(account.password_hash, self.registration["password"])
            self.assertTrue(verify_password(self.registration["password"], account.password_hash))

    def test_register_duplicate_email_returns_400_without_another_account(self):
        self.assertEqual(self.register().status_code, 201)
        duplicate = self.register(username="another_username")
        self.assertEqual(duplicate.status_code, 400, duplicate.text)
        self.assertIn("email", duplicate.json()["detail"].lower())
        self.assertEqual(self.count_accounts(), 1)

    def test_register_duplicate_username_returns_400_without_another_account(self):
        self.assertEqual(self.register().status_code, 201)
        duplicate = self.register(email="another@example.com")
        self.assertEqual(duplicate.status_code, 400, duplicate.text)
        self.assertIn("username", duplicate.json()["detail"].lower())
        self.assertEqual(self.count_accounts(), 1)

    def test_register_rejects_invalid_input_before_database_writes(self):
        for changes in (
            {"email": "invalid"}, {"username": "ab"}, {"username": "bad username"},
            {"password": "short"},
        ):
            with self.subTest(fields=list(changes)):
                response = self.register(**changes)
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.count_accounts(), 0)

    def test_register_cannot_assign_a_privileged_role_from_client_input(self):
        response = self.register(role_id=2, role="admin", is_active=False)
        self.assertEqual(response.status_code, 201, response.text)
        with Session(self.engine) as session:
            account = session.get(AdminAccount, int(response.json()["account_id"]))
            self.assertEqual(account.role_id, 1)
            self.assertTrue(account.is_active)

    def test_registered_user_can_login_and_access_the_protected_auth_endpoint(self):
        registered = self.register()
        self.assertEqual(registered.status_code, 201, registered.text)
        login = self.client.post("/api/auth/login", json={
            "email": self.registration["email"], "password": self.registration["password"],
        })
        self.assertEqual(login.status_code, 200, login.text)
        payload = login.json()
        self.assertEqual(payload["token_type"], "bearer")
        self.assertEqual(payload["user"]["role"], "user")
        me = self.client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {payload['access_token']}",
        })
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["account_id"], registered.json()["account_id"])
        self.assertEqual(me.json()["email"], self.registration["email"])

    def test_login_with_the_wrong_password_returns_401(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.client.post("/api/auth/login", json={
            "email": self.registration["email"], "password": "WrongPassword@2026",
        })
        self.assertEqual(response.status_code, 401, response.text)

    def test_inactive_account_cannot_login(self):
        registered = self.register()
        self.assertEqual(registered.status_code, 201)
        with Session(self.engine) as session:
            account = session.get(AdminAccount, int(registered.json()["account_id"]))
            account.is_active = False
            session.commit()
        response = self.client.post("/api/auth/login", json={
            "email": self.registration["email"], "password": self.registration["password"],
        })
        self.assertEqual(response.status_code, 403, response.text)

    def test_registration_does_not_depend_on_optional_email_delivery(self):
        with patch.object(auth_api, "send_reset_password_email", side_effect=RuntimeError("SMTP unavailable")) as send:
            response = self.register()
        self.assertEqual(response.status_code, 201, response.text)
        send.assert_not_called()

    def test_register_missing_required_fields_returns_422(self):
        for field in ("email", "username", "password", None):
            body = dict(self.registration) if field else {}
            if field:
                body.pop(field)
            with self.subTest(field=field):
                response = self.client.post("/api/auth/register", json=body)
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.count_accounts(), 0)

    def test_register_username_at_both_length_boundaries(self):
        for index, username in enumerate(("abc", "a" * 50)):
            with self.subTest(length=len(username)):
                response = self.register(username=username, email=f"boundary{index}@example.com")
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(response.json()["username"], username)
        self.assertEqual(self.count_accounts(), 2)

    def test_register_rejects_username_longer_than_50_characters(self):
        response = self.register(username="a" * 51)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.count_accounts(), 0)

    def test_register_accepts_eight_character_password_and_can_login(self):
        response = self.register(password="abcdefgh")
        self.assertEqual(response.status_code, 201, response.text)
        login = self.client.post("/api/auth/login", json={
            "email": self.registration["email"], "password": "abcdefgh",
        })
        self.assertEqual(login.status_code, 200, login.text)

    def test_register_null_required_fields_returns_422(self):
        for field in ("email", "username", "password"):
            with self.subTest(field=field):
                self.assertEqual(self.register(**{field: None}).status_code, 422)
        self.assertEqual(self.count_accounts(), 0)

    def test_register_empty_required_fields_returns_422(self):
        for field in ("email", "username", "password"):
            with self.subTest(field=field):
                self.assertEqual(self.register(**{field: ""}).status_code, 422)
        self.assertEqual(self.count_accounts(), 0)

    def test_register_normalizes_email_and_rejects_case_variant_duplicates(self):
        response = self.register(email="  Mixed.Case@EXAMPLE.COM  ")
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["email"], "mixed.case@example.com")
        duplicate = self.register(email="MIXED.CASE@example.com", username="another_user")
        self.assertEqual(duplicate.status_code, 400, duplicate.text)
        self.assertEqual(self.count_accounts(), 1)

    def test_register_handles_preexisting_mixed_case_email(self):
        created = self.register()
        self.assertEqual(created.status_code, 201)
        with Session(self.engine) as session:
            account = session.get(AdminAccount, int(created.json()["account_id"]))
            account.email = account.email.upper()
            session.commit()
        duplicate = self.register(username="another_user")
        self.assertEqual(duplicate.status_code, 400, duplicate.text)

    def test_register_allocates_distinct_ids_without_application_max_id_query(self):
        first = self.register()
        second = self.register(email="second@example.com", username="second_user")
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        self.assertNotEqual(first.json()["account_id"], second.json()["account_id"])
        self.assertEqual(self.count_accounts(), 2)

    def test_register_recovers_a_duplicate_that_wins_after_availability_check(self):
        self.assertEqual(self.register().status_code, 201)
        original = AccountService.check_available
        checks = 0

        async def competing_registration(service, email, username):
            nonlocal checks
            checks += 1
            if checks > 1:
                await original(service, email, username)

        with patch.object(AccountService, "check_available", new=competing_registration):
            response = self.register(username="another_user")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"], "This email is already in use.")
        self.assertEqual(self.count_accounts(), 1)

    def test_register_rolls_back_failed_commit_without_leaking_database_errors(self):
        with patch.object(AsyncAuthSession, "commit", new=AsyncMock(side_effect=SQLAlchemyError("private-db-error"))):
            response = self.register()
        self.assertEqual(response.status_code, 500, response.text)
        self.assertNotIn("private-db-error", response.text)
        self.assertEqual(self.count_accounts(), 0)
