# Sprint 4 backend API contract

FastAPI `/docs` and `/openapi.json` are the generated schema source. All admin APIs require `Authorization: Bearer <access_token>` from `POST /api/admin/login`; current database ADMIN role and active/unlocked account are checked. Missing/expired/revoked/invalidated credentials: 401; regular role: 403; missing record: 404; conflict: 409; invalid input: 422; database/configuration failure: 503. Errors follow `{"detail":"message"}` or FastAPI's `detail` validation array. No cookies are issued. Existing auth contract: `apps/backend/docs/admin-auth-api.md`.

## Account status (BE-03/04)

`PATCH /api/admin/accounts/{account_id}/status`, positive signed-64-bit ID, body `{"is_active":false}`. Only JSON booleans accepted; unknown fields rejected. Success 200:

```json
{"account_id":"2","email":"user@example.com","username":"user","role":"user","is_active":false}
```

Use `true` to reactivate. Repeated requests are idempotent. Deactivation permanently invalidates all existing tokens using a persisted credential generation; reactivation requires a fresh login. The shared guard checks availability and generation for ordinary protected endpoints too. Legacy tokens without `ver` work only while the database version remains zero. No passwords, lock metadata or internal token version are returned. No pagination/filtering applies. Self-deactivation is allowed and ends that administrator's access immediately after the request.

```sh
curl -X PATCH http://localhost:8000/api/admin/accounts/2/status -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"is_active":false}'
```

Rollout prerequisite: `apps/backend/migrations/2026-11-19_account_token_version.sql`, prepared but not applied by the agent. Deploy migration before the application. Existing tokens remain compatible until first deactivation.

## Pipeline configuration (BE-05)

All paths below start with `/api/admin/rag`. IDs are UUIDs. Retrieval settings are persisted for later integration; saving settings does not activate or change live retrieval. Reindex applies chunking and the project's pinned embedding model.

| Method/path | Request | Success |
|---|---|---|
| POST `/pipelines` | `{"name":"Heritage","chunking":{"max_chars":2400,"overlap_chars":300}}` | 201 pipeline |
| GET `/pipelines` | Optional `limit=1..100` (default 20), UUID `cursor` | 200 `{"items":[...],"next_cursor":null}` |
| GET `/pipelines/{id}` | UUID path | 200 pipeline |
| PATCH `/pipelines/{id}` | `{"expected_revision":1,"retrieval":{"top_k":15}}` | 200 pipeline; revision incremented |
| DELETE `/pipelines/{id}` | UUID path | 204 empty |

Pipeline response: `id`, `name`, `revision`, `chunking`, `embedding`, `retrieval`, UTC `created_at`/`updated_at`. Default embedding: `{"model":"BAAI/bge-m3@5617a9f61b028005a4858fdac845db406aefb181:accent-mean-v1","dimensions":1024}`. Default retrieval: `{"strategy":"opensearch-hybrid","top_k":20,"min_similarity":0.55}`. Chunk size 32..16000 characters; overlap nonnegative and less than `max_chars // 2`. Similarity finite in [0,1]; top_k 1..100. Unsupported models/strategies/fields: 422. PATCH nested objects replace their section with schema defaults. Omitted sections remain unchanged; explicit null/empty patches are rejected. Duplicate names, stale revisions, active-job edits, and deletion with any job history: 409. History is retained.

## Reindex jobs (BE-06)

- POST `/pipelines/{id}/reindex`, body `{"document_ids":["<registered-document-uuid>"]}`, 1..100 unique IDs, returns 202 job. Sources must be uploaded/indexed in the configured R2 bucket/knowledge prefix. Missing source: 404; unavailable/bucket mismatch: 409; unsafe prefix/format: 422; missing bucket configuration: 503. No URLs or local paths are accepted. Pipeline settings, source revisions and ETags are snapshotted.
- GET `/jobs/{id}` returns 200 job, or 404. Response: `id`, `pipeline_id`, `pipeline_revision`, `document_ids`, `status` (PENDING/RUNNING/COMPLETED/FAILED), `processed_documents`, `indexed_passages`, nullable safe `error`, `created_at`, nullable `started_at`/`finished_at`. Counts are actual completed checkpoints; there are no percentages.
- One PENDING/RUNNING job globally prevents overlapping source rewrites (409). Failed jobs release the slot. The requesting administrator must still be available when the worker begins.

Operator-managed worker command (not started by the agent):

```sh
python -m apps.backend.services.reindex_worker --once
# Omit --once to poll; --poll-seconds defaults to 5.
```

Apply `2026-11-19_rag_pipeline.sql` first. Worker needs existing PostgreSQL/R2/OpenSearch configuration, BGE-M3 weights and ingestion dependencies (`pipelines/ingestion/requirements.txt`). It uses R2 `IfMatch`, limits sources to 16 MiB, reuses extraction/chunking/import code, then removes only stale chunks of that bucket/source. Existing GraphRAG snapshots are immutable; rebuild them through the established snapshot workflow separately.

External writes are not transactional: a failed bulk operation can leave successful items; stable IDs support a deliberate new trigger. A killed worker leaves RUNNING and retains the slot. An operator must confirm worker termination before reconciling that job; no automatic retry/cancellation/lease takeover is claimed. Live R2/OpenSearch/model/PostgreSQL verification has not run here.
