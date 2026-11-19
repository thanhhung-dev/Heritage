# Sprint 4 backend final report

**Latest re-audit: 2026-11-20. All ten Khoa backend tasks remain DONE after two runtime corrections.** Fresh results: **179 regression tests passed, zero skips, 144 subtests**; **7 actual PostgreSQL tests passed, zero skips**; real TCP API and separate worker cloud smoke passed, with actual R2/BGE-M3/OpenSearch and a verified indexed 1024-dimensional vector. Exact commands and correction details: [backend-reaudit-2026-11-20.md](backend-reaudit-2026-11-20.md). Ready-to-run seeded manual acceptance: [backend-manual-test-vi.md](backend-manual-test-vi.md). Counts later in this document describe earlier checkpoints.

2026-11-19 (Asia/Saigon). Repository `C:\Capstone 1\Heritage`; branch `feat/sprint4-admin-auth`; starting point `023efa5`. Existing completed tasks were retained. Local commits were made frequently and separated further after the user requested twice the commit cadence. No empty commits were created.

## A. Actual architecture

FastAPI/Python, Pydantic 2 DTOs, async SQLAlchemy 2 services, PostgreSQL, Argon2/JWT identity in `account`/`roles`, persistent logout revocation. Mounted runtime uses `api/`, `services/`, `core/`, `db/`, `models/`, `schemas/`. Existing duplicate `common/`/`ai/` modules were not refactored. R2 holds source/media files; the active passage pipeline uses existing extraction/chunking, pinned BGE-M3 and OpenSearch. GraphRAG snapshots remain independently managed. Scene configuration uses existing scene/model-asset/sky columns and public viewer DTOs.

## B. Task outcomes

| Task | Status | Result |
|---|---|---|
| BE-01 | DONE | Admin login/logout retained, versioned issuance; re-audit fixed Windows server startup and verified actual HTTP login/logout |
| BE-02 | DONE, existing | Current database role and persistent logout revocation retained; regression passed |
| BE-03 | DONE | Strict administrator-only activation/deactivation API |
| BE-04 | DONE | Every protected session checks current availability and credential generation; old tokens stay invalid after reactivation |
| BE-05 | DONE | Validated persisted pipeline CRUD, optimistic revisions, cursor pagination and history-safe deletion |
| BE-06 | DONE | Durable scoped trigger/status and real worker; actual R2/BGE-M3/OpenSearch/PostgreSQL cloud acceptance passed, job COMPLETED and indexed vector verified |
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
| `core/document_text.py`, `requirements.txt`, `requirements.docker.txt` | Ship shared extraction and the existing parser pins inside the backend runtime |
| `tests/test_document_text.py`, `tests/test_reindex_storage.py`, `tests/test_rag_postgres.py`, `tests/test_rag_live.py`, `tests/test_rag_local_runtime.py`, `tests/test_rag_verifier.py`, root `scripts/sprint4/verify_rag_postgres.py` | Packaging, storage protocol, actual database/model/search/cloud acceptance and isolated verification tooling |
| root `docs/sprint4/backend-architecture-review.md`, `backend-task-plan.md`, `backend-progress.md`, `backend-api-contract.md`, `backend-test-matrix.md`, `backend-final-report.md` | Architecture, decomposition, evidence, handoff and remaining work |
| root `docs/sprint4/rag-completion-plan.md`, `manage-rag-pipeline-report.md`, `rag-runtime-setup.md` | RAG follow-up scope, installed runtime, final real-cloud evidence and cleanup |
| `__main__.py`, `services/reindex_worker.py` | Re-audit corrections: explicit Windows Selector event-loop factory for async psycopg, owned SDK client closure after each worker job |
| `tests/test_sprint4_application_postgres.py`, `tests/test_sprint4_manual_launcher.py`, root `scripts/sprint4/manual_backend.py` | Production-DDL account/3D/concurrency/cascade checks, configuration guards and a disposable actual-application/manual RAG test environment |
| root `docs/sprint4/backend-reaudit-2026-11-20.md`, `backend-manual-test-vi.md` | Current verification evidence and complete Vietnamese manual walkthrough for BE-01 through BE-10 |

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
- Scripts were not applied to the application database. Follow-up migration verification passed on PostgreSQL 18.4 inside owned disposable schemas; production/reference-version rollout remains separate.

## F. Test evidence

Interpreter: `C:\Capstone 1\.venv\Scripts\python.exe`. Initial Sprint regression command, run from repository root; subsequent RAG follow-up results are recorded below and in `manage-rag-pipeline-report.md`:

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

1. Actual PostgreSQL tests now pass on a disposable local PostgreSQL 18.4 database. Rollout against the deployment reference version/database remains through the approved process. No project/production database was modified.
2. Real R2/BGE-M3/OpenSearch/PostgreSQL reindex acceptance has passed. Operator deployments still run the explicit worker process. Retrieval settings are stored but do not automatically alter live search. Existing GraphRAG snapshots use their established export/index workflow.
3. One active reindex globally prevents overlapping source rewrites. Failed external bulk operations may leave successful items; stable IDs support deliberate new jobs. A killed worker leaves RUNNING and holds the slot until an operator confirms termination and reconciles it. No automatic retry/cancellation/recovery is claimed.
4. PostgreSQL row-lock serialization is implemented and its actual concurrent integration test passed during the RAG follow-up. SQLite tests also verified unique-safe swapping, stale requests and transaction rollback of intermediate sequence writes.
5. Shared sky presets are referenced and validated, not edited. Camera GLB references must be registered for the same scene. Asset existence means a current database record; file-content/download availability is not a live verified guarantee.

## H. Frontend handoff

Use admin bearer login, then the documented paths. A deactivated/reactivated account must sign in again; 401 means refresh the authentication flow. For pipeline edits, retain `revision` and submit `expected_revision`; treat 409 as reload/reconcile. Trigger reindex with registered document UUIDs and poll its real job state/counts; PENDING waits for the separately operated worker.

For drag-and-drop scenes, fetch all pages, exclude overview -1, and send the complete desired order plus last fetched regular ID order. Use stable scene IDs, because public s1/s2 slugs derive from sequence. PUT 3D configuration uses the existing camera field names and replaces omitted camera/sky fields with defaults/null; use array or `{x,y,z}` vectors. `model_asset_ids` asserts existing references and does not transfer assets. Public viewer camera/sky payloads and R2 URL normalization remain compatible. No frontend UI was changed.

## I. Estimates and Git

The decomposition still totals the original **84 reference hours**, every subtask <=8h. No actual engineering hours were inferred from execution time. All ten tasks satisfy scoped acceptance after the final real-cloud RAG verification. Changes are local commits only; no remote push, PR, deployment, service left running or persistent Git configuration change. Local commits use per-command `commit.gpgsign=false`, matching the earlier branch workflow with unavailable signing key.

## Earlier Manage RAG Pipeline checkpoints

The command/results in section F describe the initial Sprint run. Initial follow-up evidence in `manage-rag-pipeline-report.md` recorded worker packaging fixes, parser pins, 38 RAG regression tests plus 3 safety-guard tests and 5 actual PostgreSQL integration tests passing. Disposable databases were removed; application data was untouched. That checkpoint closed BE-08's PostgreSQL verification and still awaited RAG runtime resources; packages/weights had not yet been installed.

The user then authorized installation. OpenSearch 3.3.0, PyTorch CPU, sentence-transformers and the pinned model cache were installed; 49 RAG regression cases and 6 actual PostgreSQL/BGE-M3/OpenSearch local-runtime cases passed without skips. That local runtime used an explicit S3 response fixture. Cloud execution was refused at that stage, so BE-06 temporarily remained PARTIAL. Its owned cloud source and local test artifacts were cleaned up.

## Final Manage RAG Pipeline acceptance

The user's subsequent authorization allowed the actual cloud verification command to execute:

```powershell
& 'C:\Capstone 1\.venv\Scripts\python.exe' -X utf8 scripts/sprint4/verify_rag_postgres.py --live
```

**6 passed, zero failed, zero skipped, one existing warning, 63.18s.** This includes five real PostgreSQL cases and one actual admin/API/worker/R2/BGE-M3/OpenSearch case. The job reached COMPLETED and the indexed vector had 1024 dimensions. Storage, embeddings and search were not mocked in the cloud case. Database cases overlap the earlier local command and are not counted twice.

The fresh owned R2 source was owner/ETag checked, conditionally deleted and confirmed absent with HEAD 404. The disposable database was removed. A direct inspection found zero remaining owned search indices/pipelines. The test search process was stopped and port 19200 verified closed. Application data, existing cloud objects and untracked QA files were preserved. Runtime/cache remain installed. Exact setup and evidence are in `rag-runtime-setup.md` and `manage-rag-pipeline-report.md`. BE-05 and BE-06 are DONE; no critical task integration remains unresolved. Production/application migration and deployment remain separate operator actions.
