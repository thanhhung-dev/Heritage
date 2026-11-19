# Manage RAG Pipeline — follow-up verification

2026-11-19 (Asia/Saigon), continuing from `c6c149a` at the user's request. Scope: BE-05/BE-06. Previously completed endpoints were retained.

| Task | Current status | Evidence |
|---|---|---|
| BE-05 configuration CRUD | DONE | Existing HTTP/schema regression passes; JSONB CRUD and actual additive migration tested on local PostgreSQL |
| BE-06 trigger/status/worker | PARTIAL: final external verification blocked | Worker packaging fixed; queue concurrency/completion/failure verified on actual PostgreSQL; actual S3 and search adapters tested with protocol fixtures; full real R2/BGE-M3/OpenSearch smoke awaits explicit resources |

## Changes

- Moved existing TXT/MD/HTML/PDF extraction into `apps/backend/core/document_text.py`. Both offline ingestion and the worker reuse it. The worker no longer depends on the `pipelines/` tree, which is absent from the backend Docker image.
- Added the existing parser pins (beautifulsoup4 4.15.0, pypdf 6.20.1) to both backend requirement manifests. No packages were installed/upgraded in this session. The parsers already installed in the test interpreter match these versions.
- Added backend-only packaging/extraction tests, real S3 SDK precondition/stream tests, actual PostgreSQL queue integration, an opt-in full-stack smoke test, and a safe repeatable disposable-database verifier.
- No model, embedding ID, retrieval strategy, frontend, application database schema, cloud object or existing search index was changed. No worker remains running; all disposable PostgreSQL databases created by these checks were removed.

## Executed verification

From repository root with `C:\Capstone 1\.venv\Scripts\python.exe`:

```powershell
& 'C:\Capstone 1\.venv\Scripts\python.exe' -X utf8 -m pytest apps/backend/tests/test_rag_live.py apps/backend/tests/test_rag_pipeline_schema.py apps/backend/tests/test_rag_pipeline_api.py apps/backend/tests/test_reindex_worker.py apps/backend/tests/test_document_text.py apps/backend/tests/test_reindex_storage.py apps/backend/tests/test_r2_ingestion.py apps/backend/tests/test_opensearch.py -q
```

**38 passed, 7 skipped, 24 subtests passed**, one existing Starlette deprecation warning. Six skips need live OpenSearch; one needs the explicit full-stack environment. Earlier focused parser/ingestion/worker run: 19 passed/8 subtests; S3 SDK run: 4 passed/2 subtests. These overlap the 38-case run and are not additional unique test counts.

```powershell
& 'C:\Capstone 1\.venv\Scripts\python.exe' -X utf8 scripts/sprint4/verify_rag_postgres.py
```

**5 passed in 6.81s** on actual local PostgreSQL **18.4**, not the reference PostgreSQL 16 image. This command creates an owned `test_sprint4_<uuid>` database, runs `test_rag_postgres.py` and `test_sprint4_postgres.py`, propagates pytest's exit status and removes only that database afterwards. It refuses non-loopback connection hosts. SQL migrations are applied only inside each test's random schema; no migration is run on the application's database. A preceding direct run of the same five tests also passed (5.22s).

The PostgreSQL cases verify JSONB CRUD/migration defaults, simultaneous triggers across different pipelines sharing one writer slot, exactly one worker claim, persisted status/count/timestamps, search failure releasing the slot without marking the source indexed, and the pre-existing concurrent scene-order test. External S3/search/model boundaries in the queue tests are explicit fixtures, not live services. S3 SDK tests validate actual botocore parameter validation, Bucket/Key/IfMatch, sanitized 412 conflicts and closed bounded streams. No inference result from these fixtures is presented as a real BGE-M3 output.

The separate runner-guard suite `python -X utf8 -m pytest apps/backend/tests/test_rag_verifier.py -q` also passed: **3 passed in 1.84s**. It proves remote database URLs and incomplete live configuration are rejected before connecting, and invalid configuration does not leak credentials. Python compilation and `git diff --check c6c149a` passed. An actual Docker image build was not run: Docker's service is stopped and no engine is listening. No separate configured lint/type-check tool exists.

## Remaining full-stack step

Current environment: loopback PostgreSQL is available; OpenSearch ports 9200/19200 are closed; torch/sentence-transformers and cached BGE-M3 weights are absent from both the project test interpreter and system Python. No alternate Hugging Face cache is configured. A request for an existing OpenSearch/BGE-M3 test environment was sent to the user; no environment details have been received at this checkpoint.

The full-stack test is prepared at `apps/backend/tests/test_rag_live.py`. To run it, configure these locally (never paste secrets into chat or commit them):

- `OPENSEARCH_TEST_URL`: explicit test service; the test creates/deletes only its random `sprint4-live-test-*` index and search pipeline.
- `RAG_TEST_R2_OBJECT_KEY`: one existing TXT/MD/HTML/PDF object within `R2_KNOWLEDGE_PREFIX`; the test only performs HEAD/GET, with the existing R2 credentials/bucket. No bucket scan or object upload/delete occurs.
- Existing pinned BGE-M3 dependencies and cached weights. The test forces offline model loading and never downloads weights automatically.
- Existing loopback PostgreSQL credentials with permission to create/drop an owned disposable database.

```powershell
& 'C:\Capstone 1\.venv\Scripts\python.exe' -X utf8 scripts/sprint4/verify_rag_postgres.py --live
```

With those resources, the test exercises actual admin login -> configuration creation -> reindex trigger -> worker -> persisted COMPLETED -> real indexed passage/vector validation. It does not fall back to the application database/index. It has not run here; BE-06 remains PARTIAL until that evidence exists. Existing killed-worker/manual-reconciliation and immutable GraphRAG-snapshot limitations remain documented in `backend-api-contract.md`.
