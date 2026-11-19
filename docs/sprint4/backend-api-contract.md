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

Apply `2026-11-19_rag_pipeline.sql` first. Worker needs existing PostgreSQL/R2/OpenSearch configuration, BGE-M3 weights and backend runtime requirements (including the same document-parser versions as offline ingestion). Shared extraction ships in `apps/backend/core/document_text.py`; the image does not need the offline `pipelines/` directory. It uses R2 `IfMatch`, limits sources to 16 MiB, reuses extraction/chunking/import code, then removes only stale chunks of that bucket/source. Existing GraphRAG snapshots are immutable; rebuild them through the established snapshot workflow separately.

External writes are not transactional: a failed bulk operation can leave successful items; stable IDs support a deliberate new trigger. A killed worker leaves RUNNING and retains the slot. An operator must confirm worker termination before reconciling that job; no automatic retry/cancellation/lease takeover is claimed. Actual PostgreSQL, BGE-M3 and OpenSearch verification passes through `verify_rag_postgres.py --local-runtime` with an explicit S3 fixture. The actual R2 `--live` command was not executed because execution approval was refused. See `manage-rag-pipeline-report.md` and `rag-runtime-setup.md` for evidence and commands.

## Scenes (BE-07/08)

Base path: `/api/admin/heritages/{heritage_id}/scenes`. Resource IDs are positive signed-64-bit integers. Administrators have global scope in the current role model; the nested route additionally requires the scene to belong to the requested heritage. Missing/mismatched association: 404. No new tenant/ownership scheme is invented.

| Method/path | Request | Success |
|---|---|---|
| POST base | `{"title":"Gate","description":"History"}`; optional `sequence` | 201 scene |
| GET base | Optional `limit=1..1000` (default 100), `after_sequence>=-1` | 200 `{"items":[...],"next_after_sequence":null}` |
| GET `/{scene_id}` | IDs in path | 200 scene |
| PATCH `/{scene_id}` | Nonempty title/description patch; description may be null | 200 scene |
| DELETE `/{scene_id}` | IDs in path | 204 empty |
| PATCH `/order` | `{"scene_ids":[12,11],"expected_scene_ids":[11,12]}` | 200 ordered non-overview scene list |

Scene: `{"id":11,"heritage_id":1,"sequence":0,"title":"Gate","description":"History"}`. Titles 1..250 characters, no surrounding whitespace; descriptions <=20000. Unknown fields are rejected (422). Sequence defaults to append, accepts -1 for the unique overview, and must be within [-1,2147483647]. Duplicate sequences return 409. Metadata PATCH cannot move a scene between heritages or edit sequence; use `/order`.

Reorder requires every regular scene ID exactly once; exclude the overview. `expected_scene_ids` is the last fetched order (fetch every page first). Stale order/membership: 409; duplicate/missing/foreign IDs: 422. Empty arrays are valid for a heritage without regular scenes. The overview remains -1. Database parent-row locks serialize create/update/delete/order/config writes; two-phase temporary positive sequences preserve immediate UNIQUE constraints and roll back together on error. Reordering renumbers regular scenes from zero, which also changes derived public slugs s1/s2; stable client identity should use scene IDs. A successful reorder response includes all regular scenes without pagination. Exhausted temporary integer space: 409. Scene deletion cascades child records according to existing FKs; no stored R2 file is deleted. No new scene schema migration is required.

## Scene 3D configuration (BE-09/10)

GET `/api/admin/scenes/{scene_id}/3d-config`: 200 configuration, 404 missing scene. PUT same URL replaces camera/sky configuration, 200 saved configuration; admin bearer token required. Example:

```json
{
  "camera": {
    "node_name": "Camera_Main",
    "start_position": [1, 2, 3],
    "start_target": {"x": 0, "y": 0, "z": 0},
    "zoom_position": null,
    "zoom_target": null,
    "path_url": "models/camera.glb",
    "instant_move": false
  },
  "sky_preset_id": 1,
  "model_asset_ids": [31]
}
```

Only `camera` is required. Omitted/null `sky_preset_id` clears the selected sky. Omitted camera fields reset to null/default false; this is PUT replacement, not a patch. Position/target pairs must appear together and differ. Vectors accept exactly three finite numeric values, as arrays or exact `{x,y,z}` objects, each within ±1000000. Booleans/numeric strings are rejected as coordinates. `instant_move` is a strict boolean. Camera node names are 1..255 characters. Unknown fields: 422.

`model_asset_ids` is an optional validation assertion that every supplied ID already belongs to the scene. It does not select LODs, remove other assets or reassign ownership. Duplicates/missing/foreign assets: 422. `path_url` must match a registered GLB asset of this scene, either raw stored reference or its R2 public URL. Unsafe schemes, absolute local paths, traversal (including encoded forms), credentials, query strings and fragments are rejected. Model formats must match existing glb/splat/sog options; LOD is nonnegative. Stored values remain raw references; API responses use the existing R2 URL policy and host restrictions.

Environment configuration references existing shared sky presets rather than editing them globally. Missing preset: 422. Referenced preset numeric values must be finite: turbidity/rayleigh/exposure [0,100], mie coefficient/cloud coverage/cloud density/stars [0,1], mie directional G [-1,1], elevation [-90,90], azimuth [-360,360]. Preset lighting fields are returned using the existing viewer schema. No new viewer fields, storage blob or asset-selection schema is introduced.

Response: `scene_id`, `heritage_id`, `camera` (same viewer fields above), nullable `sky_preset_id`/`sky`, and all scene `models`. Sky uses existing aliases such as `mieCoefficient` and `cloudCoverage`; models use `id`, `file_url`, `format`, `lod_level`, nullable `compression`/`file_size_bytes`. No pagination/filtering applies. Saved camera/sky values are the same scene columns consumed by public heritage/tour endpoints, which retain their contracts.

```sh
curl http://localhost:8000/api/admin/heritages/1/scenes -H "Authorization: Bearer $TOKEN"
curl -X PUT http://localhost:8000/api/admin/scenes/11/3d-config -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"camera":{"start_position":[1,2,3],"start_target":[0,0,0]},"sky_preset_id":1}'
```
