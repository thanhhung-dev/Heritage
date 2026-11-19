# Khoa backend re-audit — 2026-11-20

Requested scope: independently re-read and verify all ten backend tasks from the Sprint 4 assignment and supplied task table. Preserve unrelated QA files and frontend work. Commit each coherent correction or verification increment locally; no push or deployment.

Baseline: `28c2d49`, branch `feat/sprint4-admin-auth`. The earlier DONE labels are previous evidence, not a substitute for this audit.

| Tasks | Review and verification | Current audit |
|---|---|---|
| BE-01/02 | Login/logout, token lifetime, revocation aliases, current database role; all admin guards | Reviewing |
| BE-03/04 | Strict account status, disabled login/session, reactivation, concurrent status changes | Reviewing |
| BE-05/06 | Config CRUD/revisions, scope, queue claims, failure handling, real R2/model/search/DB | Reviewing |
| BE-07/08 | Heritage association, CRUD/cascades, pagination, full ordering, concurrent writes | Reviewing |
| BE-09/10 | Camera/environment persistence, vector/path validation, asset ownership, public viewer | Reviewing |

Execution: inspect production paths and current tests; run the selected backend regression; reproduce and fix any defects with regression coverage; strengthen missing real-PostgreSQL checks; rerun the real RAG integration; record exact results and provide a Vietnamese manual test guide using disposable development resources.

The “Manage Knowledge” rows assigned to Khoa concern account activation/deactivation. Admin action history and heritage CRUD belong to Hùng and are outside this audit.

Results will be appended only after commands complete.

## Corrections reproduced during this audit

1. The worker did not close SDK clients it created itself. Owned clients now close on successful and failed jobs; injected clients stay with their caller. Targeted worker/storage command: **11 passed, 4 subtests**, 5.00s. An initial new-test fixture rename affected all rows; that test setup was corrected to filter by pipeline ID before the passing run.
2. A real Uvicorn process on Windows returned **503 on `/api/admin/login`**, although TestClient tests passed. A direct async connection reproduced `InterfaceError`: psycopg cannot run with ProactorEventLoop. Installed Uvicorn 0.53 explicitly chooses Proactor without reload, overriding a policy-only workaround. Added `python -m apps.backend`, which supplies an explicit Selector loop factory on Windows and keeps Uvicorn's auto loop on other platforms. With the same disposable database/server smoke, real HTTP login, scene/3D persistence, public viewer, pipeline CRUD and logout now pass. The prepared manual-test launcher will exercise this path in subsequent verification.

## Completed verification checkpoints

- Selected backend regression: **168 passed, 6 skipped, 140 subtests**, 40.26s; the skips were explicitly gated OpenSearch integrations.
- Actual OpenSearch follow-up: **11 passed, zero skips**, 18.43s, closing those six skipped cases.
- Actual PostgreSQL migrations/queue/order plus new auth/3D checks: **7 passed, zero skips**, 9.88s. New checks execute repository `schema.sql`, actual JSONB, sequences and multilevel FK cascades. An earlier nine-case run included two accidentally imported duplicate tests; import style was corrected and the seven-case run is the accurate count.
- All temporary PostgreSQL databases from these commands were removed. Application schema/data and unrelated QA files remain unchanged.
