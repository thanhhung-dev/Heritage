"""Status HTTP lifecycle against isolated storage, real JWTs and Argon2."""
import unittest

from apps.backend.api.admin import accounts
from apps.backend.core import security
from apps.backend.tests import test_admin_auth as fixtures


class AccountStatusTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.AdminAuthTests.setUpClass.__func__)
    create_database = fixtures.AdminAuthTests.create_database
    sql = fixtures.AdminAuthTests.sql
    login = fixtures.AdminAuthTests.login
    headers = staticmethod(fixtures.AdminAuthTests.headers)

    def setUp(self):
        fixtures.AdminAuthTests.setUp(self)
        self.app.include_router(accounts.router)
        self.admin_headers = self.headers(self.login().json()["access_token"])

    def status(self, active, account_id=2):
        return self.client.patch(f"/api/admin/accounts/{account_id}/status",
                                 json={"is_active": active}, headers=self.admin_headers)

    def test_deactivate_reactivate_never_revives_old_sessions(self):
        old = self.client.post("/api/auth/login", json={
            "email": "user@example.com", "password": self.password,
        }).json()["access_token"]
        self.assertEqual(self.client.get("/api/auth/me", headers=self.headers(old)).status_code, 200)
        result = self.status(False)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertFalse(result.json()["is_active"])
        self.assertNotIn("password_hash", result.text)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.headers(old)).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={
            "email": "user@example.com", "password": self.password,
        }).status_code, 403)
        self.assertEqual(self.status(False).status_code, 200)
        self.assertEqual(self.sql("SELECT token_version FROM account WHERE id=2")[0][0], 1)
        self.assertEqual(self.status(True).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.headers(old)).status_code, 401)
        new = self.client.post("/api/auth/login", json={
            "email": "user@example.com", "password": self.password,
        }).json()["access_token"]
        self.assertEqual(security.decode_access_token(new)["ver"], 1)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.headers(new)).status_code, 200)

    def test_status_validation_and_admin_permissions(self):
        url = "/api/admin/accounts/2/status"
        self.assertEqual(self.client.patch(url, json={"is_active": False}).status_code, 401)
        user = security.create_access_token({"sub": "2", "role": "admin"})
        self.assertEqual(self.client.patch(url, json={"is_active": False}, headers=self.headers(user)).status_code, 403)
        for body in ({}, {"is_active": "false"}, {"is_active": 1}, {"is_active": None},
                     {"is_active": True, "role": "admin"}):
            with self.subTest(body=body):
                self.assertEqual(self.client.patch(url, json=body, headers=self.admin_headers).status_code, 422)
        self.assertEqual(self.status(True, 999).status_code, 404)
        for invalid in (0, -1, 2**63, "invalid"):
            self.assertEqual(self.status(True, invalid).status_code, 422)

    def test_admin_login_after_reactivation_uses_new_generation(self):
        self.assertEqual(self.status(False, 1).status_code, 200)
        self.assertEqual(self.login().status_code, 401)
        self.sql("UPDATE account SET is_active=1 WHERE id=1")
        self.assertEqual(self.client.get("/protected-admin", headers=self.admin_headers).status_code, 401)
        new = self.login().json()["access_token"]
        self.assertEqual(security.decode_access_token(new)["ver"], 1)
        self.assertEqual(self.client.get("/protected-admin", headers=self.headers(new)).status_code, 200)

    def test_deleted_locked_and_invalid_version_accounts_fail_closed(self):
        for version in (True, "0", -1, 1):
            token = security.create_access_token({"sub": "2", "ver": version})
            self.assertEqual(self.client.get("/api/auth/me", headers=self.headers(token)).status_code, 401)
        self.sql("DELETE FROM account WHERE id=2")
        token = security.create_access_token({"sub": "2"})
        self.assertEqual(self.client.get("/api/auth/me", headers=self.headers(token)).status_code, 401)
