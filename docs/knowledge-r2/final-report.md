# Knowledge library backend final report

Completed 2026-11-20 on `feat/knowledge-r2-library`, based on `cc03edc`. Backend, tests and integration documents are implemented. Existing production R2 objects were not written, renamed, moved or deleted. The module does not import existing files into SQL, and uploading does not invoke RAG, embeddings, classification, chunking or indexing.

## Task results

Requested estimates are planning estimates, not actual hours worked.

| Task | Estimate | Status | Changed files | Test result |
|---|---:|---|---|---|
| BE-R2-01 R2 integration | 3h | DONE | `core/r2_library.py`, `docs/knowledge-r2/.env.example`, smoke script | PASS synthetic bucket isolation; real fixed-bucket listing and HEAD |
| BE-R2-02 Listing | 6h | DONE | R2 adapter, `schemas/knowledge_library.py`, `api/knowledge_library.py` | PASS root/nested/empty/pagination/marker mapping; real nested listing |
| BE-R2-03 Presigned upload | 6h | DONE | `services/knowledge_policy.py`, `services/knowledge_library.py`, session ORM/migration | PASS validation, signed headers/length/TTL, durable reservation and concurrent conflict |
| BE-R2-04 Completion | 4h | DONE | Library service and adapter | PASS full UTF-8/JSON verification, missing/mismatched/expired sessions, atomic publication, concurrent completion and recovery |
| BE-R2-05 File operations | 5h | DONE | Adapter, router and DTOs | PASS real metadata mapping, bounded preview, download disposition/signing and safe content handling |
| BE-R2-06 Folder/delete | 6h | DONE | Adapter and router | PASS conditional marker creation and exact-file deletion with siblings preserved; synthetic writes only |
| BE-R2-07 Security | 5h | DONE | `api/knowledge_dependencies.py`, policy, DTOs | PASS all eight auth boundaries, current DB roles/active/locked status, session ownership, finite expiry, path/type/size limits and safe errors |
| BE-R2-08 Tests/docs | 8h | DONE | Five test/support files, API/frontend/architecture/progress/report docs | PASS 35 feature tests; legacy regression exceptions detailed below |

Paths in the table are relative to `apps/backend/` unless otherwise specified. Additional integration changes are limited to mounting the router in `app.py`, importing its ORM model and excluding the migration-owned table from legacy create_all bootstrap. No frontend source, existing R2 SDK construction, media configuration, auth implementation or RAG source was modified.

## Implemented API and architecture

Eight operations are mounted beneath `/api/admin/knowledge`:

- GET `/objects` — one delimiter-based R2 listing page.
- POST `/upload-url` — durable session and 300-second, create-only staging PUT URL.
- POST `/uploads/{uploadId}/complete` — real verification and create-only publication.
- GET `/object` — current HEAD metadata.
- POST `/download-url` — 300-second attachment GET URL.
- GET `/preview` — bounded raw text in JSON, no HTML rendering.
- POST `/folders` — logical zero-byte slash marker.
- DELETE `/objects` — HEAD then one exact DeleteObject, no recursive/bulk deletion.

`KnowledgeR2` extends the existing `R2Storage` and reuses its client setup, timeouts and storage error handling. Its server-controlled bucket is always `knowledge-heritage`; invalid bucket configuration fails closed. Existing `R2_BUCKET` behavior for `heritage` and `heritage-scene` is unchanged. Scope defaults to the actual bucket root; no existing object names or folder trees are hardcoded. Folder markers and private staging are filtered, with pagination retained even on empty filtered pages.

Upload sessions persist in `knowledge_library_upload`. A unique nullable destination reservation prevents concurrent active sessions from owning the same name. Completion locks the session on PostgreSQL; verifies staging size, MIME, upload metadata and full content; spools at most the configured upload cap with a 1 MiB in-memory threshold; then writes the final key with atomic `IfNoneMatch='*'`. It never relies on HEAD alone or source-only copy conditions for no-overwrite guarantees. Published identity and a server-generated SHA-256 marker support retries after a database failure. Completed files are not recreated after deletion.

Upload/download URLs expire after 300 seconds; sessions expire after 900 seconds. Uploads accept UTF-8 Markdown, text and JSON only. Default upload limit is 10 MiB (hard configuration cap 32 MiB); default preview limit is 128 KiB (hard cap 1 MiB). JSON validation can use memory up to its bounded upload size plus parsed representation; ordinary text is validated incrementally. Preview is bounded independently. Keys and generated staging paths obey R2's 1024-byte limit. Read keys retain their original Unicode representation; new names must use NFC.

Authorization reuses the existing JWT signature configuration, rejects the public fallback key, requires a valid finite expiration and access-token purpose, then checks the current database account and ADMIN role. Non-admin/ownership failures return 403; missing/invalid credentials or inactive/locked accounts return 401. Custom metadata has an explicit response allowlist. Provider bodies, credentials, signed URLs and keys are not logged by the library's error handlers.

## Verification evidence

| Check | Result | Evidence / limits |
|---|---|---|
| Feature unit/API/SDK/migration tests | **PASS** | 30 tests across storage, API and contract modules; HTTP exercised through ASGI and actual mounted application boundary; boto3 signing and Stubber protocol verified without network |
| PostgreSQL integration | **PASS** | 5 tests on actual local PostgreSQL; migration applied in random owned schemas inside a newly created disposable `test_knowledge_*` database; separate connections raced reservations/completion; schemas and database removed afterward |
| Final combined feature run | **PASS** | **35 tests, 15.297 seconds, 0 failures/errors/skips** on final implementation |
| Real R2 read-only smoke | **PASS** | Root: 3 folders on first page; followed only the first returned folder per level through depth 6; real HEAD found a 1424-byte object and ETag. No full inventory; historical object count/total size were not re-estimated |
| Legacy targeted regression | **PARTIAL: 65 PASS, 3 existing failures/errors** | 68 tests across old admin knowledge, ingestion, startup, heritage API, DB bootstrap policy, health and catalog migration; see below |
| Alembic graph | **PASS** | `python -m alembic -c apps/backend/alembic.ini heads` reports one head, `20261120_knowledge_library` |
| Python compile validation | **PASS** | All 17 changed Python files compile; actual app import/OpenAPI tested |
| Dependency consistency | **PASS** | `python -m pip check`: no broken requirements; no dependency installation/update needed |
| Diff whitespace review | **PASS** | `git diff --check cc03edc`; backend-only scope reviewed; no private environment file or credentials committed |
| Standalone lint/type check | **NOT RUN** | No configured backend lint/type command found; ruff/mypy are not installed. Syntax/schema/runtime tests do not replace static type analysis |
| Separate backend package build | **NOT RUN** | No separate backend build target; import/compile validation completed |
| Frontend lint/type/build | **NOT RUN** | Backend-only task; no frontend changes |
| Full repository suite / live RAG infrastructure | **NOT RUN** | Targeted regressions used; existing retrieval/inference services were not started |
| Real R2 upload/delete / browser CORS acceptance | **NOT RUN** | Production mutations prohibited; SDK/HTTP writes used synthetic storage. Exact-origin CORS policy documented, not changed |
| Main application database migration | **NOT RUN** | Existing application data/schema not modified; migration tested on disposable PostgreSQL resources only |

The expected storage-failure warning in the unit log is the explicit sanitized-error test, not a failed check. The first default-Windows-encoding regression invocation also exposed encoding-dependent legacy behavior; the canonical run used `python -X utf8` as documented.

Legacy exceptions were reproduced with the **pre-task `cc03edc` app entrypoint** and unchanged legacy modules:

1. `AdminKnowledgeTests.test_actual_app_registers_admin_router`: the older `/api/admin/storage/entries` router is already unmounted. This task mounts the new `/api/admin/knowledge` router; it does not expose the older local/RAG administration surface.
2. `AdminKnowledgeTests.test_existing_file_registration_and_real_index_guard`: existing SQLite temporary-file cleanup raises Windows `NotADirectoryError` for `test.db`.
3. `R2IngestionTests.test_transcript_config_metadata_is_preserved_and_header_alone_is_rejected`: existing ingestion transcript metadata assertion fails.

The baseline check reproduced 2 failures and 1 error for these exact three tests. Their source, pipeline code and old storage service are unchanged; they were not rewritten to make this feature appear green. Local detailed logs are in the workspace's `.catalog-test-runtime/knowledge-final-tests.log`, `knowledge-regression-utf8.log` and `knowledge-baseline-utf8.log`.

## Configuration and rollout remaining

Reuse server-side `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `DATABASE_URL`, `JWT_SECRET_KEY`. New documented settings are `R2_KNOWLEDGE_BUCKET=knowledge-heritage`, optional `R2_KNOWLEDGE_LIBRARY_PREFIX`, `KNOWLEDGE_MAX_UPLOAD_BYTES` and `KNOWLEDGE_PREVIEW_MAX_BYTES`. Credentials were available for safe R2 reads. The inspected local `.env` has no private JWT_SECRET_KEY; the library therefore intentionally refuses authenticated access with the legacy fallback until startup is configured correctly.

Deploy migration `20261120_knowledge_library`, whose parent is `20261120_classification`, through the reviewed migration process. It adds only the session table, indexes and constraints. Do not stamp a database that lacks the parent schema. Do not substitute legacy create_all. Downgrade is guarded to prevent silently dropping upload recovery records; export/retire sessions before reviewed removal. The application database was not migrated during this work.

Review bucket-scoped credentials, configure exact Admin origins in both backend CORS_ORIGINS and R2 CORS, and use a real active admin account. Gateway rate limits are a deployment responsibility because the repository has no existing distributed limiter. Review staging-only lifecycle/DB retention separately; abandoned staging and recovery records are retained and no cleanup job/policy was installed. Signed URLs must not be logged or persisted by consumers.

Delete acts on the current exact key after HEAD. R2 documentation does not provide a promised conditional DeleteObject contract, so this implementation does not claim compare-and-delete behavior against independent external replacements. Coordinate external writers during user-confirmed deletion. No production delete was tested.

For request/response/error details use [API contract](api-contract.md). For exact browser upload sequence, progress, CORS policy and dedicated-environment manual tests use [frontend integration and manual acceptance](frontend-integration.md). No deployment, push, PR, production CORS edit or production object mutation was performed.
