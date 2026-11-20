# Admin knowledge library API

Base path: `/api/admin/knowledge`. All eight operations require `Authorization: Bearer <access-token>` from the existing login API and a currently active, unlocked ADMIN account. Password reset tokens cannot authorize these operations. Upload sessions belong to the administrator who created them. No endpoint accepts a bucket; requests with unknown body fields fail with 422.

Successful responses have `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. JSON responses contain text as data, never executable HTML. `/docs` and `/openapi.json` include schemas, bearer security and operation-specific errors.

## Browse a folder

`GET /objects?prefix=documents/&limit=100&continuationToken=...`

- `prefix`: exact slash-terminated prefix; omit to use configured root (bucket root by default). Explicit `prefix=` means bucket root and is rejected if a narrower scope is configured.
- `limit`: 1–1000, default 100; counts R2 entries including prefixes/markers before filtering.
- `continuationToken`: optional opaque token from the previous response; URL-encode it, retain the same prefix. Do not parse or increment it.

```json
{
  "bucket": "knowledge-heritage",
  "prefix": "documents/",
  "folders": [{"name": "history", "prefix": "documents/history/"}],
  "files": [{"name": "overview.md", "key": "documents/overview.md", "size": 123, "lastModified": "2026-11-20T08:00:00Z"}],
  "nextContinuationToken": null
}
```

This is synthetic example data. One `ListObjectsV2(Prefix, Delimiter='/')` request supplies each page. Common prefixes are logical folders, files stay at their current level, and marker objects are excluded from files. Empty/missing prefixes return empty arrays. Private staging is excluded. A filtered page can be empty and still contain a next token; keep paging until the token is null. Browsing never registers/imports objects into a database or downloads file contents.

## Request an upload URL

`POST /upload-url` → **201**

```json
{"folder":"documents/history/","filename":"notes.md","contentType":"text/markdown","size":123}
```

```json
{
  "uploadId": "00000000-0000-0000-0000-000000000001",
  "objectKey": "documents/history/notes.md",
  "uploadUrl": "<ephemeral-presigned-staging-url>",
  "method": "PUT",
  "expiresIn": 300,
  "sessionExpiresAt": "2026-11-20T08:15:00Z",
  "requiredHeaders": {"Content-Type":"text/markdown","If-None-Match":"*","x-amz-meta-upload-id":"00000000-0000-0000-0000-000000000001"}
}
```

Upload precisely the declared bytes to `uploadUrl`, without wrapping them in FormData. URL validity is 300 seconds; durable completion sessions last 900 seconds. `Content-Length` is signed and must match `size`; browsers set it automatically from the File/Blob. Clients must send every returned required header unchanged.

Uploads support `.md`/`text/markdown`, `.txt`/`text/plain` and `.json`/`application/json`. Size must be positive and at most `KNOWLEDGE_MAX_UPLOAD_BYTES` (default 10 MiB; deployment maximum 32 MiB). Whole-file UTF-8 validation and JSON validation occur during completion. No indexing/OCR/classification follows upload.

New names must be NFC Unicode, at most 255 UTF-8 bytes, and cannot contain separators, control/format characters, URL/path metacharacters or surrounding whitespace. Keys/prefixes are at most 1024 UTF-8 bytes and reject absolute paths, traversal, repeated separators, backslashes, percent-encoded paths and URI/drive prefixes. Existing Unicode keys are used exactly, without normalization. Uploads outside configured scope or inside the reserved staging prefix are rejected.

The default conflict policy is **reject**, never rename/overwrite: an existing destination or an active reservation returns 409. Atomic conditional destination PUT also rejects a writer that races the preliminary HEAD. A reserved session persists across process restarts and backend instances. A signing/transaction failure may require retry or session expiry; never assume a network timeout proves failure.

## Complete an upload

`POST /uploads/{uploadId}/complete` → **200**, no request body.

```json
{
  "uploadId":"00000000-0000-0000-0000-000000000001",
  "status":"stored",
  "object":{"bucket":"knowledge-heritage","key":"documents/history/notes.md","name":"notes.md","size":123,"contentType":"text/markdown","lastModified":"2026-11-20T08:00:05Z","etag":"\"example-etag\"","metadata":{}}
}
```

The backend locks the database session, HEADs staging, validates signed identity/MIME/size, reads the full object conditionally against its ETag into a bounded disk spool, validates actual content and publishes with `If-None-Match: *`. It verifies the final HEAD and persists completion. Caller-supplied keys, ETags or sizes never select the completed object.

Repeated completion returns the same stored object after a real HEAD. If the final object was removed, return 404 without recreating it. If it changed, return 409. If publication succeeded but the DB commit was lost, the final upload identity allows recovery on retry, including after session expiry. An expired, unpublished session returns **410**; missing staging/session returns 404; incorrect ownership returns 403; size/MIME/identity/content mismatch returns 422. A competing destination write returns 409. Failed validation never publishes the destination.

## File metadata

`GET /object?key=documents/history/notes.md` → **200**, the `object` shape above without its enclosing wrapper. Reads actual `HeadObject`. Only `language` and `source-type` user metadata are exposed. Arbitrary custom metadata, upload bookkeeping, storage response headers and provider internals are not exposed. Folder marker keys are not accepted as files.

## Short download URL

`POST /download-url` with `{"key":"documents/history/notes.md"}` → **200**

```json
{"key":"documents/history/notes.md","downloadUrl":"<ephemeral-presigned-get-url>","expiresIn":300}
```

HEAD must succeed before signing. GET uses attachment disposition, a safely encoded filename and `application/octet-stream`. The URL is a temporary bearer capability; never log or persist it. Objects remain private; no public object URL is generated. A link can return changed content if an independent writer replaces that key before use.

## Safe text preview

`GET /preview?key=documents/history/notes.md` → **200**

```json
{"key":"documents/history/notes.md","content":"# Example\nPlain source text","contentType":"text/plain; charset=utf-8","size":123,"etag":"\"example-etag\""}
```

The HTTP response is `application/json`; `contentType` describes the embedded source text. Render `content` as a text node or escaped code block. Do not feed it to `innerHTML` or an unsanitized Markdown renderer. Reads at most configured preview bytes + 1 using Range and If-Match, then closes the body. Maximum defaults to 128 KiB, capped at 1 MiB. Errors: **413** too large, **415** unsupported extension, 422 binary/invalid UTF-8 or JSON, 409 changed/incomplete content, 404 missing object. Empty existing `.txt`/`.md` files are supported.

## Create a logical folder

`POST /folders` with `{"parentPrefix":"documents/","folderName":"history"}` → **201**

```json
{"name":"history","prefix":"documents/history/"}
```

Creates a zero-byte slash marker with a create-only conditional PUT. Existing marker/prefix or a file with the same name returns 409. Existing folders are discoverable without markers; no marker is inserted during browsing. Parent prefixes are logical and need not have physical markers. No folder rename/move/delete endpoint exists.

## Delete exactly one file

`DELETE /objects` with `{"key":"documents/history/notes.md"}` → **204**, no body. HEAD must find the exact object first. Empty/root/slash-terminated keys, recursive flags, arrays and extra bucket fields fail validation. The only storage mutation is `DeleteObject(Key=the_exact_key)`; siblings and marker objects are untouched. Missing object returns 404. No bulk or recursive operation exists.

Deletion targets the current object at that key. R2's documented S3 write-condition table does not promise conditional DeleteObject; this API does not promise ETag-based compare-and-delete. If an independent tool replaces the same key between HEAD and deletion, its current contents can be deleted. Coordinate outside writers when confirming deletions. Production deletion was not exercised during implementation.

## Common errors and usage

Error bodies follow FastAPI's `{"detail":"safe message"}` convention; schema-validation details are an array. Missing/invalid/expired access token → 401 (`WWW-Authenticate: Bearer`); non-admin → 403; validation → 422; missing object/session → 404; conflict → 409; storage/configuration/database unavailable → 503. Unexpected provider messages and credentials are never returned. Provider-rejected opaque pagination tokens currently return sanitized 503; restart listing without that token.

Example read-only request (shell variables are placeholders):

```bash
curl --get "$API_BASE/api/admin/knowledge/objects" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  --data-urlencode 'prefix=documents/' --data-urlencode 'limit=100'
```

Production operators must provision the migration, private JWT signing configuration, current admin accounts, private bucket-scoped R2 permissions and exact-origin CORS. Rate limiting belongs to the existing deployment gateway; no distributed limiter was present in this repository. See [frontend integration](frontend-integration.md) for browser behavior and manual acceptance steps.
