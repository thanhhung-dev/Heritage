# Sprint 4 backend final report

2026-11-19 (Asia/Saigon). Repository `C:\Capstone 1\Heritage`; branch `feat/sprint4-admin-auth`; starting point `023efa5`. Existing completed tasks were retained. Local commits were made frequently and separated further after the user requested twice the commit cadence. No empty commits were created.

## A. Actual architecture

FastAPI/Python, Pydantic 2 DTOs, async SQLAlchemy 2 services, PostgreSQL, Argon2/JWT identity in `account`/`roles`, persistent logout revocation. Mounted runtime uses `api/`, `services/`, `core/`, `db/`, `models/`, `schemas/`. Existing duplicate `common/`/`ai/` modules were not refactored. R2 holds source/media files; the active passage pipeline uses existing extraction/chunking, pinned BGE-M3 and OpenSearch. GraphRAG snapshots remain independently managed. Scene configuration uses existing scene/model-asset/sky columns and public viewer DTOs.

## B. Task outcomes

| Task | Status | Result |
|---|---|---|
| BE-01 | DONE, existing | Admin login/logout retained, version claim integrated into existing issuance |
| BE-02 | DONE, existing | Current database role and persistent logout revocation retained; regression passed |
| BE-03 | DONE | Strict administrator-only activation/deactivation API |
| BE-04 | DONE | Every protected session checks current availability and credential generation; old tokens stay invalid after reactivation |
| BE-05 | DONE | Validated persisted pipeline CRUD, optimistic revisions, cursor pagination and history-safe deletion |
| BE-06 | PARTIAL verification | Durable scoped trigger/status, concurrent duplicate protection and real worker implemented; live external smoke test outstanding |
| BE-07 | DONE | Heritage-scoped scene CRUD, authorization, pagination and child-record cascades |
| BE-08 | DONE after follow-up | Locked atomic reorder, pinned overview, stale-order guard and rollback; actual concurrent PostgreSQL test passed during RAG follow-up |
| BE-09 | DONE | Persist/read/replace existing scene camera/sky fields, viewer-compatible model and sky responses |
| BE-10 | DONE | Finite bounded vectors, valid poses, safe paths, same-scene asset/GLB references and sky validation |

DONE means implementation, documented contract and relevant isolated tests pass. It does not imply production migration or deployment. Module B retains the assignment's account-status scope despite its Manage Knowledge label.

## C. Changed files

Paths below are relative to `apps/backend/` unless prefixed otherwise.

| Paths | Purpose |
|---|---|
| `api/admin/accounts.py`, `schemas/account_status.py`, `services/account_status.py` | Account-status endpoint, strict DTO and atomic generation updates |
| `core/security.py`, `services/account_access.py`, `services/admin_auth.py`, `api/auth.py`, `models/admin.py` | Current-account checks and versioned admin/public/Google credentials |
| `models/rag_pipeline.py`, `schemas/rag_pipeline.py`, `services/rag_pipeline.py`, `api/admin/rag.py`, `models/__init__.py` | Persisted pipeline/job models, validation, CRUD, job scheduling/status |
| `services/reindex_worker.py`, `core/search.py`, root `pipelines/ingestion/ingest_r2.py` | Real queue consumer, scoped stale-chunk removal and reusable existing extraction |
| `schemas/admin_scene.py`, `services/admin_scene.py`, `api/admin/scenes.py`, `models/scene.py` | Scoped CRUD/order, DTOs and alignment with existing schema constraints |
| `schemas/scene_config.py`, `services/scene_config.py`, `api/admin/scene_config.py` | Viewer-compatible configuration persistence and validation |
| `app.py` | Mount four new administrative routers |
| `migrations/2026-11-19_account_token_version.sql`, `migrations/2026-11-19_rag_pipeline.sql` | Additive prepared database rollout scripts |
| `tests/test_account_status.py`, `tests/test_admin_auth.py`, `tests/test_admin_knowledge.py` | Account/session cases and updated/shielded isolated fixtures |
| `tests/test_rag_pipeline_schema.py`, `tests/test_rag_pipeline_api.py`, `tests/test_reindex_worker.py`, `tests/test_opensearch.py` | RAG validation, HTTP/queue concurrency, worker and source-pruning coverage |
| `tests/test_admin_scenes.py`, `tests/test_scene_config_schema.py`, `tests/test_scene_config_api.py`, `tests/test_heritage_api.py` | Scene/config integrity and existing public viewer regression; missing nullable fixture field corrected |
| `tests/test_sprint4_postgres.py` | Opt-in disposable-schema migration/JSONB/concurrent-order verification |
| root `docs/sprint4/backend-architecture-review.md`, `backend-task-plan.md`, `backend-progress.md`, `backend-api-contract.md`, `backend-test-matrix.md`, `backend-final-report.md` | Architecture, decomposition, evidence, handoff and remaining work |

No frontend files or pre-existing untracked QA artifacts were edited/staged. The small extraction export is required for worker reuse; it preserves existing ingestion behavior and does not change another module's business logic.

## D. API inventory

Sixteen new operations; generated OpenAPI includes them and their Pydantic schemas:

| Methods | Path |
|---|---|
| PATCH | `/api/admin/accounts/{account_id}/status` |
| POST, GET | `/api/admin/rag/pipelines` |
| GET, PATCH, DELETE | `/api/admin/rag/pipelines/{pipeline_id}` |
| POST | `/api/admin/rag/pipelines/{pipeline_id}/reindex` |
| GET | `/api/admin/rag/jobs/{job_id}` |
| POST, GET | `/api/admin/heritages/{heritage_id}/scenes` |
| GET, PATCH, DELETE | `/api/admin/heritages/{heritage_id}/scenes/{scene_id}` |
| PATCH | `/api/admin/heritages/{heritage_id}/scenes/order` |
| GET, PUT | `/api/admin/scenes/{scene_id}/3d-config` |

Existing auth/public/knowledge routes retain their URLs. Error/response bodies, examples, pagination, scope and replacement semantics are documented in `backend-api-contract.md`; `/docs` and `/openapi.json` remain the generated schema system.

## E. Database changes

- `account.token_version INTEGER NOT NULL DEFAULT 0`: preserves legacy sessions until the first deactivation, then permanently invalidates older generations. Apply before application rollout.
- New `rag_pipeline` and `rag_reindex_job`: JSONB settings/snapshots, revision/time/status/count metadata, RESTRICT history relationship, checked state and unique active writer slot. No new queue dependency.
- Scene UNIQUE/CHECK definitions were aligned in ORM with the existing `schema.sql`; no new scene table or 3D blob is introduced. Existing camera-path/sky migrations remain prerequisites for the existing viewer schema.
- Scripts were prepared, not applied to the application database. Live migration verification is gated by an explicit test URL and was skipped.

## F. Test evidence

Interpreter: `C:\Capstone 1\.venv\Scripts\python.exe`. Final command, run from repository root:

```powershell
& 'C:\Capstone 1\.venv\Scripts\python.exe' -X utf8 -m pytest apps/backend/tests/test_account_status.py apps/backend/tests/test_admin_auth.py apps/backend/tests/test_admin_knowledge.py apps/backend/tests/test_rag_pipeline_schema.py apps/backend/tests/test_rag_pipeline_api.py apps/backend/tests/test_reindex_worker.py apps/backend/tests/test_admin_scenes.py apps/backend/tests/test_scene_config_schema.py apps/backend/tests/test_scene_config_api.py apps/backend/tests/test_sprint4_postgres.py apps/backend/tests/test_heritage_api.py apps/backend/tests/test_startup_config.py apps/backend/tests/test_profile_schema_validation.py apps/backend/tests/test_health.py apps/backend/tests/test_opensearch.py apps/backend/tests/test_r2_ingestion.py apps/backend/tests/test_ingestion_package.py apps/backend/tests/test_passages.py apps/backend/tests/test_db_init.py apps/backend/tests/test_chat_api.py -q
```

**155 passed, 8 skipped, 133 subtests passed in 33.02s; zero failed.** One existing Starlette/AnyIO deprecation warning. Six skips require `OPENSEARCH_TEST_URL`; two require `SPRINT4_POSTGRES_TEST_URL`.

Other successful checks:

- `python -X utf8 -m compileall -q apps/backend pipelines/ingestion/ingest_r2.py`.
- Actual `app.openapi()` generation: 35 total paths, 19 admin paths; all new routes enumerated successfully. One initial shell quoting error in the inspection command was corrected before this successful run.
- `git diff --check 023efa5`.

No separate backend build/lint/type-check task was configured; ruff/mypy were not installed and no dependencies were installed. Syntax compilation is not claimed as type checking. Full collection was not run because it includes live database/model scripts; in particular the existing profile-consent integration fixture creates tables/accounts using the application URL. Worker tests use external adapters, not live R2/model/OpenSearch. Docker inspection could not connect to its missing daemon named pipe; no Docker services were launched.

Test environment versions: FastAPI 0.141.1, Pydantic 2.13.5, SQLAlchemy 2.0.54, pytest 9.1.1, aiosqlite 0.21.0, PyJWT 2.15.1. Repository pins PyJWT 2.10.1; that exact version was not reinstalled/tested. Early failures from naive SQLite timestamps, expected-error cursor cleanup and duplicate rename handling were corrected. Existing Windows ingestion artifact reads required UTF-8 mode. The previously documented missing `camera_path_url` fake-row field was added and the public viewer suite now passes.

## G. Remaining dependencies and limits

1. Run opt-in PostgreSQL tests against a disposable named test database, then use the approved migration rollout process. No project/production database was modified.
2. Verify a real test-source reindex with actual R2, existing BGE-M3 weights and OpenSearch; run the separate worker process explicitly. Retrieval settings are stored but do not automatically alter live search. Existing GraphRAG snapshots need their established export/index workflow.
3. One active reindex globally prevents overlapping source rewrites. Failed external bulk operations may leave successful items; stable IDs support deliberate new jobs. A killed worker leaves RUNNING and holds the slot until an operator confirms termination and reconciles it. No automatic retry/cancellation/recovery is claimed.
4. PostgreSQL row-lock serialization is implemented and an actual concurrent integration test is present; it has not run here. SQLite tests verified unique-safe swapping, stale requests and transaction rollback of intermediate sequence writes.
5. Shared sky presets are referenced and validated, not edited. Camera GLB references must be registered for the same scene. Asset existence means a current database record; file-content/download availability is not a live verified guarantee.

## H. Frontend handoff

Use admin bearer login, then the documented paths. A deactivated/reactivated account must sign in again; 401 means refresh the authentication flow. For pipeline edits, retain `revision` and submit `expected_revision`; treat 409 as reload/reconcile. Trigger reindex with registered document UUIDs and poll its real job state/counts; PENDING waits for the separately operated worker.

For drag-and-drop scenes, fetch all pages, exclude overview -1, and send the complete desired order plus last fetched regular ID order. Use stable scene IDs, because public s1/s2 slugs derive from sequence. PUT 3D configuration uses the existing camera field names and replaces omitted camera/sky fields with defaults/null; use array or `{x,y,z}` vectors. `model_asset_ids` asserts existing references and does not transfer assets. Public viewer camera/sky payloads and R2 URL normalization remain compatible. No frontend UI was changed.

## I. Estimates and Git

The decomposition still totals the original **84 reference hours**, every subtask <=8h. No actual engineering hours were inferred from execution time. After the Manage RAG Pipeline follow-up, nine tasks satisfy acceptance and BE-06 retains PARTIAL external verification status. Changes are local commits only; no remote push, PR, deployment, service left running or persistent Git configuration change. Local commits use per-command `commit.gpgsign=false`, matching the earlier branch workflow with unavailable signing key.

## Manage RAG Pipeline follow-up

The command/results in section F describe the initial Sprint run. Current scoped results and changed paths are in `manage-rag-pipeline-report.md`: worker packaging fixed, parser dependencies declared, 38 RAG regression tests plus 3 safety-guard tests and 5 actual PostgreSQL integration tests passed. Disposable databases were created and removed; application data was untouched. BE-08's PostgreSQL concurrency check is now verified. BE-06 still needs real R2/BGE-M3/OpenSearch resources for the prepared full-stack smoke test. No model packages/weights were installed, Docker service started or production operation performed.
