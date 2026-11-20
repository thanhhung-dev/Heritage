# Knowledge library architecture review

The backend is Python 3.11, FastAPI, Pydantic 2, asynchronous SQLAlchemy 2 and PostgreSQL. Alembic owns reviewed schema changes. API routers are mounted in `apps/backend/app.py`; `/docs` and `/openapi.json` describe the public HTTP contract.

`core/r2.py:R2Storage` already owns boto3 construction, SigV4 signing, bounded connection timeouts and sanitized storage errors. The library extends that adapter, without another SDK client implementation. Existing media configuration and the legacy knowledge/RAG service remain unchanged. The old service restricts browsing to `curated/`, assigns UUID destination names and checks OpenSearch; those business rules cannot serve this library.

The new `/api/admin/knowledge` router uses the existing JWT signing primitives plus a current database account/role check. Missing credentials return 401; non-admin accounts return 403. A missing or public fallback signing secret fails closed. All storage calls select the server-controlled `knowledge-heritage` bucket. No route accepts a bucket or arbitrary URL.

## Implementation plan

1. Centralize exact key/prefix, Unicode, type and size validation. Preserve existing keys; never normalize or rename stored objects.
2. Map R2 delimiter listings and HEAD metadata into stable DTOs, including opaque pagination.
3. Add one durable upload-session table through an additive Alembic migration. Reserve active destination keys across processes with a unique constraint.
4. Sign a create-only PUT to a unique staging key. Bind content type, length and upload identity. Verify the entire bounded object before publishing with atomic `PutObject(IfNoneMatch='*')` to the requested destination. A preliminary HEAD is only an early conflict check.
5. Serialize completion using a database row lock. Final upload metadata allows recovery after storage succeeds but the database commit fails. Repeated completion checks the real final object rather than trusting client claims.
6. Add bounded UTF-8 preview, short download links, conditional folder markers and exact-file deletion. No recursive operations or RAG ingestion.
7. Test with synthetic storage and disposable database resources; live R2 verification is read-only listing/HEAD only. Write API, CORS, rollout and manual integration documentation.

## Configuration and boundaries

Reuse `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `DATABASE_URL` and `JWT_SECRET_KEY`. Set `R2_KNOWLEDGE_BUCKET=knowledge-heritage` (default); another value is rejected. `R2_KNOWLEDGE_LIBRARY_PREFIX` optionally restricts the library, defaulting to the bucket root. The old `R2_KNOWLEDGE_PREFIX` and `R2_BUCKET` retain their existing meanings elsewhere.

New limits: `KNOWLEDGE_MAX_UPLOAD_BYTES` (default 10 MiB, maximum 32 MiB), `KNOWLEDGE_PREVIEW_MAX_BYTES` (default 128 KiB, maximum 1 MiB). Upload/download URLs last 300 seconds; upload sessions last 15 minutes. Supported uploads are UTF-8 `.md`, `.txt`, `.json`; HTML, executables, PDF/OCR and arbitrary binaries are excluded.

No rate-limit/cache middleware exists in the inspected backend. Deployment must enforce authenticated per-admin request limits at its gateway; upload size, URL expiry and durable active-key reservations also bound this workflow. No production bucket CORS policy is changed by this implementation.

## Storage correctness references

Cloudflare documents atomic create-only `PutObject` conditions in [conditional operations](https://developers.cloudflare.com/r2/api/s3/conditional-operations/) and [consistency guarantees](https://developers.cloudflare.com/r2/reference/consistency/). Source-only `CopySourceIfMatch` does not prevent overwriting the destination, so this implementation uses a bounded verified stream and conditional destination PUT. Staging is private and excluded from the library. Expired staging cleanup is an operator-owned, prefix-restricted lifecycle decision; no production cleanup is run automatically.
