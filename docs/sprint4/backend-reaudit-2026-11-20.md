# Khoa backend re-audit — 2026-11-20

Requested scope: independently re-read and verify all ten backend tasks from the Sprint 4 assignment and supplied task table. Preserve unrelated QA files and frontend work. Commit each coherent correction or verification increment locally; no push or deployment.

Baseline: `28c2d49`, branch `feat/sprint4-admin-auth`. The earlier DONE labels are previous evidence, not a substitute for this audit.

| Tasks | Review and verification | Current audit |
|---|---|---|
| BE-01/02 | Login/logout, token lifetime, revocation aliases, current database role; all admin guards | DONE; Windows startup corrected and real HTTP verified |
| BE-03/04 | Strict account status, disabled login/session, reactivation, concurrent status changes | DONE; actual PostgreSQL concurrency and HTTP lifecycle passed |
| BE-05/06 | Config CRUD/revisions, scope, queue claims, failure handling, real R2/model/search/DB | DONE; SDK lifecycle corrected; actual separate server/worker cloud flow passed |
| BE-07/08 | Heritage association, CRUD/cascades, pagination, full ordering, concurrent writes | DONE; real PostgreSQL DDL, ordering and multilevel cascades passed |
| BE-09/10 | Camera/environment persistence, vector/path validation, asset ownership, public viewer | DONE; JSONB persistence and production public viewer passed |

Execution: inspect production paths and current tests; run the selected backend regression; reproduce and fix any defects with regression coverage; strengthen missing real-PostgreSQL checks; rerun the real RAG integration; record exact results and provide a Vietnamese manual test guide using disposable development resources.

The “Manage Knowledge” rows assigned to Khoa concern account activation/deactivation. Admin action history and heritage CRUD belong to Hùng and are outside this audit.

Final result: all ten scoped backend tasks pass the re-audit. Two runtime defects were corrected; manual acceptance is now reproducible with a disposable seeded server.

## Corrections reproduced during this audit

1. The worker did not close SDK clients it created itself. Owned clients now close on successful and failed jobs; injected clients stay with their caller. Targeted worker/storage command: **11 passed, 4 subtests**, 5.00s. An initial new-test fixture rename affected all rows; that test setup was corrected to filter by pipeline ID before the passing run.
2. A real Uvicorn process on Windows returned **503 on `/api/admin/login`**, although TestClient tests passed. A direct async connection reproduced `InterfaceError`: psycopg cannot run with ProactorEventLoop. Installed Uvicorn 0.53 explicitly chooses Proactor without reload, overriding a policy-only workaround. Added `python -m apps.backend`, which supplies an explicit Selector loop factory on Windows and keeps Uvicorn's auto loop on other platforms. With the same disposable database/server smoke, real HTTP login, scene/3D persistence, public viewer, pipeline CRUD and logout now pass. The prepared manual-test launcher will exercise this path in subsequent verification.

## Completed verification checkpoints

- Selected backend regression: **168 passed, 6 skipped, 140 subtests**, 40.26s; the skips were explicitly gated OpenSearch integrations.
- Actual OpenSearch follow-up: **11 passed, zero skips**, 18.43s, closing those six skipped cases.
- Actual PostgreSQL migrations/queue/order plus new auth/3D checks: **7 passed, zero skips**, 9.88s. New checks execute repository `schema.sql`, actual JSONB, sequences and multilevel FK cascades. An earlier nine-case run included two accidentally imported duplicate tests; import style was corrected and the seven-case run is the accurate count.
- All temporary PostgreSQL databases from these commands were removed. Application schema/data and unrelated QA files remain unchanged.

## Final verification of the current source

Run from `C:\Capstone 1\Heritage` using the installed workspace virtual environment:

```powershell
$py='C:\Capstone 1\.venv\Scripts\python.exe'
$env:OPENSEARCH_TEST_URL='http://127.0.0.1:19200'
$tests=@(
  'test_account_status','test_admin_auth','test_admin_knowledge',
  'test_rag_pipeline_schema','test_rag_pipeline_api','test_reindex_worker',
  'test_admin_scenes','test_scene_config_schema','test_scene_config_api',
  'test_heritage_api','test_startup_config','test_profile_schema_validation',
  'test_health','test_opensearch','test_r2_ingestion','test_ingestion_package',
  'test_passages','test_db_init','test_chat_api','test_document_text',
  'test_reindex_storage','test_rag_verifier','test_sprint4_manual_launcher'
) | ForEach-Object { "apps/backend/tests/$_.py" }
& $py -X utf8 -m pytest @tests -q --tb=short
& $py -X utf8 scripts/sprint4/verify_rag_postgres.py
```

- Selected regression: **179 passed, zero failed/skipped, 144 subtests passed, 77.59s**. Includes all six real OpenSearch integrations, current worker cleanup tests and manual-launcher guard cases.
- PostgreSQL command: **7 passed, zero failed/skipped, 17.89s**. Five existing migration/queue/order cases plus two production-DDL account/scene/3D application cases. All operate inside owned disposable storage.
- Each pytest command reports the same existing Starlette/AnyIO deprecation warning. There is no unresolved test failure.

Real TCP/process verification, with the cached model and test search settings from the manual guide:

```powershell
& $py -X utf8 scripts/sprint4/manual_backend.py --check
# Also set HF_HUB_CACHE, EMBEDDING_DEVICE=cpu and OMP/MKL_NUM_THREADS=4:
& $py -X utf8 scripts/sprint4/manual_backend.py --rag --check
```

Both commands completed successfully. The second was executed with the network permission needed for real R2, following the user's existing authorization. It launches the mounted application and production worker in separate processes, reaches COMPLETED through real HTTP login/create/trigger/status, then directly reads the actual OpenSearch result and verifies its count and **1024-dimensional vector**. No cloud/model/search fixture is substituted. The earlier sandbox-network attempt failed before cloud setup; its owned database/index were still cleaned up. No rejected execution remains unresolved.

`python -X utf8 -m compileall -q apps/backend scripts/sprint4`, `python -m pip check`, generated `app.openapi()` and `git diff --check` all completed successfully. OpenAPI has 35 paths, including 19 admin paths. No dedicated backend build/lint/type-check task is configured; ruff and mypy are absent, so those checks are not claimed. Full unrelated model/database test collection is intentionally excluded because some tests target the application database. No frontend change or UI verification is claimed.

Independent cleanup inspection confirmed **zero** Sprint 4 disposable databases, owned search indices/pipelines, and objects under the dedicated R2 Sprint 4 test prefix (not truncated). The search process started for this audit was stopped; no API/worker was intentionally left running. Installed packages and model cache remain available.

Manual handoff: [backend-manual-test-vi.md](backend-manual-test-vi.md). Its first command starts the seeded sandbox; `--rag` adds the actual external dependency flow. Task IDs, route methods and DTO behavior remain as documented in the API contract.
