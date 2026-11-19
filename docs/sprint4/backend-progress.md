# Sprint 4 backend progress

Starting checkpoint: 2026-11-19, `023efa5`, `feat/sprint4-admin-auth`. Existing untracked QA files preserved. Estimates are planning references.

| Task | Estimate | Status | Implementation | Testing |
|---|---:|---|---|---|
| BE-01 | 8h | DONE | Existing admin login/logout, skipped | Previous report: isolated auth tests passed |
| BE-02 | 6h | DONE | Existing role guard/revocation, skipped | Previous report: isolated auth tests passed |
| BE-03 | 4h | DONE | Strict PATCH account status, admin guard, persisted atomic updates | Account/auth/knowledge targeted suite: 41 passed, 49 subtests |
| BE-04 | 8h | DONE | Shared current-account/version guard, versioned public/admin/Google tokens, additive SQL | Disabled login, old sessions, idempotence and reactivation verified; SQLite only |
| BE-05 | 10h | TODO | Pipeline settings API missing | Not run |
| BE-06 | 14h | TODO | Durable reindex jobs/worker missing | Not run |
| BE-07 | 10h | TODO | Admin scene CRUD missing | Not run |
| BE-08 | 8h | TODO | Admin scene ordering missing | Not run |
| BE-09 | 8h | TODO | Admin 3D configuration API missing | Not run |
| BE-10 | 8h | TODO | Admin 3D validation missing | Not run |

Current task: BE-05/06. Next step: persisted pipeline configuration and job APIs. BE-03/04 files: `api/admin/accounts.py`, `schemas/account_status.py`, `services/account_status.py`, `services/account_access.py`, shared security/login/model modules, version migration, `tests/test_account_status.py` and existing auth/knowledge fixture schema. Command: `python -m pytest apps/backend/tests/test_account_status.py apps/backend/tests/test_admin_auth.py apps/backend/tests/test_admin_knowledge.py -q`: 41 passed, 49 subtests, one existing Starlette warning. No project database/migration touched.
