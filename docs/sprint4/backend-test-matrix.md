# Sprint 4 backend test matrix

Tests exercise actual FastAPI handlers, JWTs, Argon2 and isolated SQLite transactions unless identified otherwise. Worker tests run real extraction, chunking, import validation and queue transitions with injected R2/OpenSearch/embedding adapters; they do not download model weights or contact live services.

| Task | Cases | Evidence |
|---|---|---|
| BE-01 | Valid admin credentials, unknown account, wrong password, malformed login, unique expiring token, logout | `test_admin_auth.py` |
| BE-02 | Regular/forged role, current database permission, missing/malformed/expired/reset token, revoked reuse, concurrent logout | `test_admin_auth.py`, `test_admin_knowledge.py` |
| BE-03 | Activate/deactivate, repeated status update, strict boolean, invalid ID, unknown account, unauthorized role | `test_account_status.py` |
| BE-04 | Disabled public/admin login, existing ordinary/admin sessions, reactivation requires new generation, bad generation, deleted account | `test_account_status.py`, existing auth guards |
| BE-05 | Create/read/update/delete, supported defaults, invalid chunk/model/retrieval settings, cursor pagination, duplicate name/rename, stale revision | `test_rag_pipeline_schema.py`, `test_rag_pipeline_api.py` |
| BE-06 | Persist pending/status, scope/bucket/prefix checks, active-job edit/delete rejection, simultaneous trigger, competing worker claims | `test_rag_pipeline_api.py`, `test_reindex_worker.py` |
| BE-06 | Actual orchestration completion/counts, failed embedding, no prune before successful indexing, changed source, disabled requester | `test_reindex_worker.py` with external adapters |
| BE-06 | Prune source/bucket filter, preserve replacement IDs, delete conflicts, partial bulk failure, dependency errors | `test_opensearch.py` transport tests |
| BE-07 | Heritage-scoped CRUD, missing/cross-heritage association, metadata validation, cascade deletion, pagination, all operations protected | `test_admin_scenes.py` |
| BE-08 | Immediate UNIQUE-safe swap, pinned overview, duplicate/missing/foreign IDs, stale order, rollback of temporary slots after actual SQL trigger failure | `test_admin_scenes.py` |
| BE-08 | Concurrent PostgreSQL reorder: one successful writer and one stale 409 | `test_sprint4_postgres.py`: passed on actual PostgreSQL 18.4 during RAG follow-up |
| BE-09 | Save/read/replace configuration, camera vectors persisted, sky/model response, raw/R2 public URL round-trip, public camera path | `test_scene_config_api.py`, `test_heritage_api.py` |
| BE-10 | Numeric strings/bools/infinity/range, invalid pose pairs, unknown fields, traversal/encoded paths/schemes/secrets, missing/foreign assets, missing/invalid sky, restricted hosts/rollback, admin permission | `test_scene_config_schema.py`, `test_scene_config_api.py` |
| Database rollout | Apply both additive SQL scripts, default credential version, JSONB pipeline CRUD | `test_sprint4_postgres.py`: passed in disposable PostgreSQL schemas; application database unchanged |
| BE-06 runtime | Extract documents without offline pipeline files; UTF-8/HTML/PDF errors | `test_document_text.py`: passed |
| BE-06 storage | Real S3 SDK Bucket/Key/IfMatch, 412 sanitization, bounded reads and closed streams | `test_reindex_storage.py`: passed with botocore protocol fixtures |
| BE-06 persistence | Actual PostgreSQL simultaneous triggers/worker claims, completion/counts and sanitized dependency failure | `test_rag_postgres.py`: passed; external adapters are explicit test fixtures |
| BE-06 live | Admin login -> trigger -> real R2/BGE-M3/OpenSearch -> indexed vector | `test_rag_live.py`: prepared, skipped until explicit resources exist |
| Test isolation | Refuse remote database URLs or missing live resources before connection; sanitize invalid configuration | `test_rag_verifier.py`: 3 passed |

Live integrations deliberately require explicit test configuration:

- `SPRINT4_POSTGRES_TEST_URL`: `postgresql+psycopg://.../<test_... or ..._test>`. Tests only create/drop a random schema they own; never fall back to application `DATABASE_URL`.
- `OPENSEARCH_TEST_URL`: existing tests create/delete their own random index and search pipeline.
- R2/real BGE-M3 end-to-end worker smoke test still needs operator-provided test resources and weights. No live test credentials have been created or committed.

Existing `test_profile_consent.py` is not run: it uses application `DATABASE_URL`, creates tables and registers accounts rather than requiring a disposable test target. Full backend collection also includes live model/database scripts. The selected regression suite covers all changed modules without touching the project database. UTF-8 mode is required on this Windows host for existing ingestion tests reading Vietnamese artifact text with default encoding.
