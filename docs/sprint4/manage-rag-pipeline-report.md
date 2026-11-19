# Manage RAG Pipeline — follow-up verification

2026-11-19 (Asia/Saigon), continuing from `c6c149a` at the user's request. Scope: BE-05/BE-06. Previously completed endpoints were retained.

| Task | Current status | Evidence |
|---|---|---|
| BE-05 configuration CRUD | DONE | Existing HTTP/schema regression passes; JSONB CRUD and actual additive migration tested on local PostgreSQL |
| BE-06 trigger/status/worker | DONE | Actual R2/BGE-M3/OpenSearch/PostgreSQL cloud smoke passed; job reached COMPLETED and a real 1024-dimensional indexed vector was verified |

## Final acceptance verification

The user renewed authorization to run all remaining checks. The actual cloud command was then executed successfully, superseding the earlier refusal recorded below:

```powershell
& 'C:\Capstone 1\.venv\Scripts\python.exe' -X utf8 scripts/sprint4/verify_rag_postgres.py --live
```

**6 passed, zero failed, zero skipped, one existing warning, 63.18s.** Five cases cover real PostgreSQL migrations/JSONB/queue/concurrency; the sixth runs actual admin login -> pipeline create -> reindex trigger -> production worker function -> real R2 HEAD/GET with ETag -> pinned BGE-M3 CPU inference -> actual OpenSearch -> persisted COMPLETED/counts -> real indexed vector verification. R2, embedding and search were not mocked in this cloud case. The earlier 49-case RAG regression remains passing evidence. The five database cases overlap the previous local-runtime run and are not counted twice.

A fresh uniquely owned R2 test document was conditionally created for the run. Cleanup checked its owner marker and ETag, conditionally deleted it and verified HEAD 404. The disposable PostgreSQL database was removed; direct inspection found zero remaining owned search indices/pipelines. The test OpenSearch process was stopped and port 19200 verified closed. Application data, existing cloud objects and existing untracked QA files remain unchanged. Installed runtime/cache are retained. No worker, push or deployment remains in progress.

BE-05 and BE-06 now meet the task acceptance criteria. Operator rollout requirements, single-writer behavior, manual reconciliation after a killed worker and separate immutable GraphRAG snapshot maintenance remain documented behavior, rather than unfinished integration. The sections below preserve earlier verification milestones.

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

## Previous full-stack checkpoint (superseded by installed-runtime results below)

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

## Installed runtime — earlier checkpoint

The user subsequently authorized installing missing components. OpenSearch 3.3.0 (official SHA512 verified), torch 2.9.1+cpu, sentence-transformers 6.1.0 and the exact pinned BGE-M3 weights are installed. Actual model inference produced finite normalized 1024-dimensional vectors. Windows search runs with the installed Java 21, explicit Faiss DLL path and test-only absolute disk watermarks. No Docker/Windows service or application `.env` was modified.

Current evidence: **49 RAG regression tests passed, 24 subtests passed, zero skipped** (28.89s), including all actual OpenSearch cases. **6 PostgreSQL/local-runtime tests passed, zero skipped** (60.15s), including actual admin/API/worker/BGE-M3/search interaction and vector verification. These are 55 distinct selected cases; only the object-storage response in the local runtime case is a fixture. The earlier separate 11-case search run overlaps the 49.

The actual R2 `--live` command was rejected at execution approval with `Rejected("rejected by user")`; no further reason was supplied. It did not run and was not resubmitted. The explicit `--local-runtime` mode performs no cloud call and does not claim cloud success. The runtime and weights are no longer missing; the sole remaining full-stack assertion requires permission to execute the cloud test.

The owned temporary cloud object was created with approval, then owner/ETag checked, conditionally deleted and confirmed absent by HEAD 404. All temporary PostgreSQL databases, search test indices/pipelines and the search process were cleaned up; port 19200 is closed. Installed artifacts/cache remain available. See `rag-runtime-setup.md` for exact commands, version details, resolved startup errors and restart instructions. No source configuration/record from the application was changed, and existing untracked QA files remain excluded.
