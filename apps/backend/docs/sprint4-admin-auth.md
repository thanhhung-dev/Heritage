# Sprint 4: Admin authentication

## Repository inspection

| Area | Existing behavior | Relevant files | Action |
|---|---|---|---|
| Authentication | Mounted FastAPI email/password and Google login; Argon2, PyJWT; inactive duplicate public/auth implementation | api/auth.py, core/security.py, app.py | Reuse active helpers and response DTOs; add admin endpoints |
| Authorization | Core guard trusts JWT role only; split admin router uses it but is unmounted | core/security.py, api/admin/router.py | Check current database role, active/locked state; mount existing router |
| Identity | Active compatibility AdminAccount maps integer account.id and roles.id; common/models contains a different legacy model | models/admin.py, api/auth.py | Use active account/roles; do not create another identity model |
| Token | HS256, 7-day expiry, hardcoded fallback, wrong PyJWT exception class; no refresh tokens | core/security.py, common/security.py | Environment key, required claims, optional issuer/audience, explicit token type |
| Logout | No endpoint or persistent revocation | api/auth.py | Admin logout and persistent SHA-256 token denylist; preserve other sessions |
| Database | SQLAlchemy async PostgreSQL; standalone dated SQL migrations are tracked; Alembic env exists without tracked revisions/config | db/base.py, migrations/ | Add additive dated SQL migration; do not apply it |
| Tests | unittest, FastAPI TestClient, temporary SQLite/aiosqlite tests | tests/test_admin_knowledge.py | Add HTTP/security tests using real hashing, JWT and database queries |
| Errors/config | FastAPI detail responses, validation 422, dotenv loaded during app import | schemas/auth.py, app.py | Preserve response contract; document new variables |

Only backend files change. Existing untracked QA files are excluded from commits.

## Subtasks (planning estimates, not elapsed time)

| ID | Work / files | Hours | Depends on | Acceptance criteria | Status |
|---|---|---:|---|---|---|
| BE-01.1 | Inspect active routing, identity and tests; this document | 1 | — | Identify active vs legacy implementations | DONE |
| BE-01.2 | Admin login service/router, schemas/auth.py | 2 | BE-01.1 | Valid admin gets token; bad credentials 401; regular user 403; invalid body 422 | DONE |
| BE-01.3 | Harden core/security.py, common/security.py compatibility | 2 | BE-01.1 | Environment signing key, expiry, type, signature and optional issuer/audience validation | DONE |
| BE-01.4 | Admin logout service/router, revocation model and SQL migration | 1 | BE-01.2, BE-01.3 | Revoke only presented credential; repeat logout safe | DONE |
| BE-01.5 | tests/test_admin_auth.py; API examples | 2 | BE-01.4 | Login/logout cases run against actual handlers | DONE |
| BE-02.1 | Inspect role lookup and admin routing; this document | 1 | BE-01.1 | Reuse account.role_id and roles table | DONE |
| BE-02.2 | Server-side guard, admin routers, app.py | 2 | BE-02.1 | Missing token 401, non-admin 403, valid admin allowed; public routes stay public | DONE |
| BE-02.3 | Database denylist checked by shared authentication | 2 | BE-01.4 | Revoked token rejected on protected endpoints across sessions/workers | DONE |
| BE-02.4 | Authorization/revocation tests and final report | 1 | BE-02.2, BE-02.3 | Run targeted regression, review diff, report actual results | DONE |

Total: BE-01 8h + BE-02 6h = 14h. PostgreSQL persistence is necessary: existing active account has no session store, and an in-memory denylist would not survive workers/restarts. No new dependency, Redis, frontend change, database reset, migration execution, remote push or deployment.

Implementation and isolated verification are complete. See [API documentation](admin-auth-api.md) and [completion report](sprint4-admin-auth-report.md). The SQL migration is an operator rollout step; real PostgreSQL deployment verification remains pending. Shared database storage supports multiple workers by design; automated tests exercise separate sessions/clients and concurrent logout, without starting multiple production workers.
