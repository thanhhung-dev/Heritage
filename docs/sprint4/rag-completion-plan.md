# Manage RAG Pipeline completion follow-up

2026-11-19. User requested completing Manage RAG Pipeline and reporting when finished; earlier authorization for autonomous work and frequent small local commits still applies. Keep the existing BE-05 CRUD and BE-06 queue instead of rebuilding them.

Findings after `c6c149a`:

- Local PostgreSQL 18.4 is reachable. The two existing opt-in PostgreSQL tests passed in a newly created disposable `test_sprint4_<uuid>` database. It was removed afterwards; the application database was not migrated or written. This verifies actual PostgreSQL JSONB CRUD/migration behavior, using version 18 rather than the deployment reference version 16.
- Worker extraction imports `pipelines/ingestion/ingest_r2.py`, but the backend Docker image only copies `apps/backend` and corpus. The runtime manifests also omit the extraction packages already pinned in `pipelines/ingestion/requirements.txt`. A packaged worker would fail to process a document even with its other services configured.
- OpenSearch is not listening on loopback. Docker service is stopped. BGE-M3 weights and torch/sentence-transformers are absent in the current test interpreter. Cloud R2 configuration exists, but no remote write is authorized or needed for this follow-up.

Execution plan:

1. Move the existing extraction implementation into a shared backend core module, import it from the offline ingestion CLI and worker, and include the existing parser dependency versions in both runtime manifests. Preserve normalization, PDF and HTML behavior; do not change models or retrieval strategy.
2. Test extraction with the offline `pipelines` package deliberately unavailable, plus R2 SDK response/precondition/stream handling and worker error checkpoints. Add PostgreSQL queue/worker integration cases with explicitly identified external adapters.
3. Re-run RAG schema/API/worker/ingestion/search regressions and live PostgreSQL tests in a disposable database. Add opt-in end-to-end checks for actual R2/model/OpenSearch resources and run them if those resources become available.
4. Commit each coherent fix/test/docs increment. Report implementation and live verification separately. Do not label a mocked embedding/search run as a live full-stack success.
