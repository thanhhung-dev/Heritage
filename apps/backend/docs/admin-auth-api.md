# Admin authentication API

The active backend is `apps.backend.app:app`. Interactive OpenAPI documentation is available at `/docs`; the schema is at `/openapi.json`.

## Configuration and database preparation

Use the existing PostgreSQL `DATABASE_URL` and active `account` / `roles` schema. Accounts are administrators only when their current `account.role_id` resolves to `roles.name = ADMIN` (case insensitive). Public registration continues to create regular users; these endpoints never promote accounts.

Copy variables from [admin-auth.env.example](admin-auth.env.example) into the repository root `.env` or process environment. This example file is not loaded automatically.

| Variable | Required | Behavior |
|---|---|---|
| `JWT_SECRET_KEY` | Yes for authentication | Random signing secret, preferably 32+ random bytes. No default secret. Missing key returns 503. Must match across workers. |
| `JWT_ISSUER` | No | When set, issuance adds `iss` and verification requires that issuer. |
| `JWT_AUDIENCE` | No | When set, issuance adds `aud` and verification requires that audience. |
| `DATABASE_URL` | Yes for authentication | Existing asynchronous PostgreSQL connection. |

Before enabling this version, an operator must apply [2026-11-17_revoked_access_token.sql](../migrations/2026-11-17_revoked_access_token.sql) using the project's dated SQL migration process. The migration adds only `revoked_access_token` and its expiry index. It does not modify accounts or existing rows. It has been prepared, **not executed against the project database**. Do not use `create_all()` in production.

All authenticated endpoints now check the database denylist. Missing database configuration or missing revocation schema returns 503; credentials are never accepted when the revocation check fails. Public routes remain public. Enabling issuer/audience validation invalidates earlier tokens missing those claims. Removing the previous fallback key also rejects tokens signed using that fallback.

## POST /api/admin/login

No bearer token required. Content type: `application/json`.

```json
{
  "email": "admin@example.com",
  "password": "<account-password>"
}
```

Email is validated and normalized as in the existing email/password login contract. Password must be nonempty. Argon2 checks run in the thread pool. Unknown accounts, wrong passwords, inactive accounts and accounts locked until a future time return the same 401 message. Valid credentials for a regular user return 403.

Success: **200**, with `Cache-Control: no-store` and `Pragma: no-cache`.

```json
{
  "access_token": "<signed-access-token>",
  "token_type": "bearer",
  "user": {
    "account_id": "1",
    "email": "admin@example.com",
    "username": "admin",
    "role": "admin"
  }
}
```

Admin access tokens last **60 minutes**, include a unique `jti`, `iat`, `exp`, `sub`, `type=access` and existing identity claims. They contain no password/hash/secret. There is no refresh-token mechanism in the active backend, so none is introduced. Existing public-login token lifetime remains seven days.

## POST /api/admin/logout

Header: `Authorization: Bearer <access_token>`. No request body.

Success: **204**, empty response, `Cache-Control: no-store`. The server verifies the JWT and the account's current admin permission, then atomically inserts a canonical SHA-256 credential digest and expiry into PostgreSQL. It never stores the raw JWT. Equivalent base64url spellings of the same signature map to the same digest.

Repeated and concurrent logout returns 204 while the token remains unexpired and the account remains an active, unlocked admin. An expired token returns 401. Tokens issued by the existing public login can also be logged out when their account is currently an admin. Logout affects only the presented credential; other sessions remain valid.

After logout, reusing the token on `/api/auth/me`, profile endpoints or any protected admin API returns **401**. Authentication checks the shared database on every request, without a per-worker in-memory cache. Requests already authorized before logout can finish.

## Protected admin routes

The existing knowledge router is mounted under `/api/admin`: storage entries/folders, document metadata/download/chunks and upload lifecycle routes. Every operation requires a valid unrevoked JWT and an active, unlocked account whose **current database role** is ADMIN. JWT/client role values cannot grant this permission. Demotion, disabling or locking blocks subsequent admin requests.

Knowledge administration also retains its existing environment, loopback and Origin restrictions: local/test environment, loopback connection and host, allowed Origin when present. An authenticated admin outside these restrictions receives 403. Login/logout are separate from these local-only knowledge restrictions. The split `api/admin/router.py` also uses the shared guard, but remains unmounted to avoid duplicate paths.

## Error responses

| HTTP | Meaning | Example |
|---|---|---|
| 401 | Wrong login credentials, missing bearer, invalid/expired/reset/revoked access token, unavailable account on protected admin routes | `{"detail":"Incorrect email or password."}` or `{"detail":"Token has been revoked."}` |
| 403 | Authenticated account lacks current ADMIN role, or knowledge local-access restriction fails | `{"detail":"Administrator permission required."}` |
| 422 | Missing/invalid JSON fields | Standard FastAPI validation response, `{"detail":[...]}` |
| 503 | Signing key/database/schema not available | `{"detail":"Authentication database unavailable; check configuration and migrations."}` |

401 responses include `WWW-Authenticate: Bearer`. API errors do not include bearer tokens, passwords, SQL statements or database exception details. These endpoints use Authorization headers and set no authentication cookie; cookie/CSRF settings do not apply.

## Verification

From the repository root, using the existing environment (no dependency installation):

```powershell
& 'C:\Capstone 1\.venv\Scripts\python.exe' -m pytest `
  apps/backend/tests/test_admin_auth.py `
  apps/backend/tests/test_admin_knowledge.py `
  apps/backend/tests/test_startup_config.py `
  apps/backend/tests/test_profile_schema_validation.py `
  apps/backend/tests/test_health.py -q
```

Tests run real Argon2 and JWT validation, current-role queries and revocation persistence against isolated SQLite databases. Storage/network services are replaced only in tests; production authentication is never mocked. See [the completion report](sprint4-admin-auth-report.md) for actual results and PostgreSQL verification limits.
