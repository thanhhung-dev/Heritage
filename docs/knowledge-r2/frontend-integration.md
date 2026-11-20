# Frontend integration and manual acceptance

This change supplies backend APIs only. Existing R2 objects immediately appear through listings; no import, copy, rename or upload is required. Use the admin login API and its bearer access token. Never send the admin token to R2.

## Exact upload flow

1. Admin opens Knowledge Library. Request `GET /api/admin/knowledge/objects`, with no prefix to start at the server-configured root.
2. Render `folders` and `files`. Navigate using each returned `prefix`, retain each exact `key`, and use URLSearchParams for query strings. Fetch additional pages using `nextContinuationToken` until null, even after an empty filtered page. Reset pagination when changing folders.
3. Admin selects the destination folder and one local File. Match its extension to the API's explicit MIME allowlist; do not rely on browser `file.type` being populated.
4. POST `/api/admin/knowledge/upload-url` with `{folder, filename, contentType, size: file.size}`. A 409 means the name is occupied or reserved by an active upload; ask the admin to choose another name. The backend never silently renames files.
5. PUT the raw File to the returned `uploadUrl`, using every `requiredHeaders` entry. Do not use multipart/FormData, do not add Authorization, and do not manually set Content-Length from browser JavaScript. The browser computes that signed header from the exact File body.
6. After the PUT succeeds, POST `/api/admin/knowledge/uploads/{uploadId}/complete` with the admin bearer token and no body. Do not treat the R2 PUT alone as completed library storage.
7. Backend verifies staging and publishes atomically. Display `Stored` after completion returns 200. This status does not mean indexed, embedded or available to the chatbot.
8. Refresh the selected folder listing. Preserve the selected prefix, clear old pagination and display the exact destination returned by completion.

Use `XMLHttpRequest.upload.onprogress` for direct PUT progress (`loaded/total`). A progress value of 100% means transfer finished; show a separate `Verifying upload…` state while completing. Fetch can upload the same File but does not provide the same portable upload-progress event.

If a PUT response is lost, retrying the immutable staging key can return 412 because the first PUT succeeded. Call complete to find out; do not remove If-None-Match or overwrite staging. After a completion network error/503, retry complete with the same upload ID. A completed session returns its real object; a missing final object is not recreated. An expired unpublished session returns 410 and needs a new session. Signed URLs expire after five minutes, sessions after fifteen. Keep URLs only in memory and redact them from analytics and error reports.

## Browser CORS configuration

There are two separate policies: backend `CORS_ORIGINS` for authenticated API requests, and bucket CORS for direct PUT/GET to R2. The bucket stays private. An administrator must review and apply exact deployment origins in Cloudflare; implementation did not change production policies. Replace the illustrative domain below with the actual Admin origin, including scheme and port. Add localhost only in a reviewed development policy.

Cloudflare dashboard CORS policy shape:

```json
[
  {
    "AllowedOrigins": ["https://admin.example.com"],
    "AllowedMethods": ["PUT", "GET", "HEAD"],
    "AllowedHeaders": ["Content-Type", "Content-Length", "If-None-Match", "x-amz-meta-upload-id"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 300
  }
]
```

Do not add wildcard origins/headers or DELETE permission for this flow. Delete requests go to the authenticated backend. `OPTIONS` is handled as CORS preflight and is not an AllowedMethods entry. When using the S3 API to configure CORS, wrap the rule array in `{"CORSRules":[...]}`; do not replace an existing policy without review. Use the R2 S3 endpoint in generated URLs, not a public/custom CDN hostname.

Include an `Origin` header when examining CORS with command-line tools. Test the browser preflight from the actual Admin origin and confirm the three required upload headers are accepted. Signed URL expiration may appear to JavaScript as a CORS/network error because R2 omits CORS headers on expired responses; request a fresh session or retry completion when the original upload may already exist. See [Cloudflare CORS documentation](https://developers.cloudflare.com/r2/buckets/cors/) and [presigned URL documentation](https://developers.cloudflare.com/r2/api/s3/presigned-urls/).

## Metadata, preview, download and deletion

GET `/object?key=...` for actual size, MIME, timestamps, ETag and allowed metadata. GET `/preview?key=...` returns escaped JSON containing raw UTF-8 text; display through text nodes/`<pre>`. Markdown/HTML strings must not execute. A 413 offers download instead. POST `/download-url` with `{key}` and open its short-lived attachment URL. No permanent private URL is needed.

For creation, POST `/folders` with `{parentPrefix, folderName}` and refresh. For deletion, show a confirmation containing the exact filename/key, then send one DELETE `/objects` body `{key}`. Refresh after 204. Never submit a folder prefix, a wildcard, an array or `recursive`; all are outside this contract. Coordinate external writers because deletion acts on the current object at the selected key, without an atomic ETag-delete guarantee.

## Deployment and manual test steps

1. Configure the server variables in [.env.example](.env.example). Reuse existing R2 credentials and database conventions. Use a private `JWT_SECRET_KEY`, never the repository's legacy public fallback. Existing login and this module must use the same signing configuration before process startup.
2. Review Alembic history before applying `20261120_knowledge_library` (parent `20261120_classification`) through the normal deployment migration process. It creates only `knowledge_library_upload`; it does not rewrite existing rows or R2 objects. Do not use create_all or stamp an incompatible database. The implementation's PostgreSQL tests applied it only to disposable resources.
3. Provision an active admin account through the existing account flow, verify its `roles` record is ADMIN, and log in. Open backend `/docs`, click Authorize and enter its bearer token. Confirm all eight library operations appear.
4. Safe production read checks: list root; click a returned folder prefix; page with a low limit; inspect one existing file; preview a small text file; request a short download link. Do not assume any sample folder names exist. Confirm 401 without a token and 403 for an ordinary user.
5. Perform **write/delete acceptance only in a dedicated test environment**, using a bucket/account with synthetic data and the required bucket name `knowledge-heritage`. Set a dedicated library scope such as `qa-library/` and create test filenames there. Never select existing production files for these checks.
6. Create a logical QA folder, request an upload URL for a small UTF-8 `.md`, PUT the exact bytes and complete. Confirm listing/metadata/preview match the bytes; repeat complete and confirm the same result. Confirm there is no chatbot/RAG ingestion.
7. Request another session with that filename and expect 409. Try `.html`, wrong MIME, zero/oversize, traversal and recursive-delete fields; expect 422. On the dedicated test resource, verify size/identity mismatch cannot complete and an expired session returns 410.
8. Delete only the synthetic file using its exact returned key; expect 204, then 404 on metadata. Confirm a sibling test file and the folder marker remain. No recursive folder-delete operation is provided.

## Automated verification commands

From repository root, with the existing backend virtualenv and test dependencies:

```text
python -X utf8 -m unittest apps.backend.tests.test_knowledge_library_storage apps.backend.tests.test_knowledge_library_api -v
python -X utf8 -m unittest apps.backend.tests.test_knowledge_library_postgres -v
python -X utf8 scripts/verify-knowledge-r2.py
```

For PostgreSQL tests, explicitly set `KNOWLEDGE_TEST_DATABASE_URL` to a loopback `postgresql+psycopg://.../test_*` database dedicated to automated tests. Without it, those tests skip. They apply the migration inside randomly named owned schemas and clean up only those schemas. Every R2 write/delete in tests goes to a synthetic in-memory client. The smoke script allows only real R2 listing and HEAD and never prints file names, credentials or signed URLs.

Abandoned staging objects and old session records are retained for recovery. Operators should review a lifecycle policy restricted to the reserved `__knowledge_library_uploads__/` prefix under the configured root, with retention comfortably beyond session expiry; no cleanup/lifecycle policy was installed. Keep recovery records and audit/retention requirements in mind before database pruning. Apply per-admin upload/write rate limits at the deployment gateway because this repository has no existing distributed limiter.
