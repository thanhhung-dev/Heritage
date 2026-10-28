# Persisted chat API

`POST /api/chat/message` creates a conversation or appends a user/assistant pair
to an existing account-owned conversation. It uses the same OpenSearch/BGE/LLM
pipeline and evidence gates as `POST /api/chat`, whose contract remains available.

```json
{
  "message": "Lang Tu Duc duoc xay dung khi nao?",
  "conversation_id": null,
  "heritage_id": null,
  "heritage_context": {"title": "Lang Tu Duc"},
  "scene_context": "Cong chinh"
}
```

Response `201` contains `conversation_id`, assistant `message_id`, `answer`,
normalized `citations`, `resolution_status`, and `answer_type`. Citations store
their own UUID, message UUID, source title, optional source URL and relevance
score. Original passage provenance also remains in the existing message JSON.

Both the full chat page and an embedded heritage/scene chat can use this same
persisted endpoint. Contracts live in `schemas/chat.py`. Both response formats
include `needs_user_choice`, `suggestions`, `corrected_from`, `corrected_to`,
`intent`, `entity_id`, `abstained` and `abstention_reason`:

- A grounded answer has citations and `abstained=false`.
- A clarification has `needs_user_choice=true`, the question in `answer`, and
  optional candidate `suggestions`. It is not an abstention and may have no citations.
- Missing evidence has `abstained=true`, `abstention_reason=insufficient_evidence`
  and no invented citations.
- The compatibility response can report unavailable retrieval with
  `abstention_reason=service_unavailable`. Persisted chat treats unavailability
  as a failed request, unless its labelled local fallback is enabled.

Assistant outcome metadata is stored in `chat_message.response_metadata` and
restored as the same top-level fields in the message history API. The database
evidence constraint also permits an explicitly marked clarification. Existing
messages retain their stored abstention flag; unavailable historical metadata
uses response defaults rather than being inferred from message text.

`POST /api/chat` remains a stateless HTTP-200 compatibility interface, using
`LegacyChatRequest` / `LegacyChatResponse`. It accepts the same heritage/scene
context and retains `sources` instead of normalized `citations`. Its optional
`session_id` is deprecated, is not an authentication credential and does not
grant history access. Both interfaces always require source evidence for factual
answers, including when a legacy client sends `use_rag=false`.

Authenticated requests use `Authorization: Bearer <access_token>`. Account IDs
come exclusively from the verified JWT and the current `account` table. Invalid
tokens are rejected; they never silently become guest requests. No account ID
is accepted in the request body. Existing conversation ownership is checked
before retrieval or inference.

Guests can send a message without Authorization, creating a conversation with
null `account_id`. A conversation UUID is not an authentication credential:
guests cannot append to saved conversations or claim a guest conversation after
login. Persisted history is reserved for its authenticated owner.

Heritage IDs must refer to published heritage. Optional heritage/scene context
qualifies the question; it is not inserted into the source evidence. Empty or
oversized messages/context are rejected with `422`.

## Bounded conversation context

Both request formats accept optional `conversation_context`:

```json
{
  "message": "Còn kiến trúc?",
  "conversation_id": null,
  "heritage_context": {"title": "Chùa Thiên Mụ"},
  "scene_context": "Cổng chính",
  "conversation_context": [
    {"role": "user", "content": "Chùa Thiên Mụ ở đâu?"},
    {"role": "assistant", "content": "Chùa ở Huế."}
  ]
}
```

The example uses the persisted endpoint. Omit `conversation_id` for the
stateless compatibility endpoint. Context accepts at most 6 messages, 2,000
characters per message and 6,000 total content characters. Only `user` and
`assistant` roles are accepted; extra fields and system/developer/tool messages
are rejected. It is prompt context, never citation evidence or imported history.

For an existing account-owned `conversation_id`, the backend checks ownership,
then loads only the most recent 6 stored messages and applies the same character
budget. Clients must omit `conversation_context` when resuming saved history;
attempting to replace it returns `400`. Another account or a guest receives
`403` before history reaches retrieval or inference.

The model receives previous messages separately from newly retrieved source
passages. Referencing follow-up questions can use the latest previous user
question to qualify retrieval, without treating previous assistant text as
evidence. Explicit topic changes keep a fresh retrieval query. Both llama.cpp
and the optional Gemini development fallback receive the bounded context.

When a conversation has `heritage_id` and a request omits `heritage_context`,
the backend loads the published heritage title/region to qualify the request.
An embedded chat should send its current `scene_context` with every question;
the backend does not invent a scene or infer private scene state.

Guest requests create independent guest conversations and can carry bounded
client context between turns. Client context itself is not persisted as extra
messages and does not grant access to any saved conversation.

The complete answer pipeline is awaited with a 30-second timeout (`504`);
the stateless compatibility route uses the same deadline.
Outside local development, persisted inference/dependency failures return a Vietnamese `500` response. A missing DB
configuration returns `503`. The conversation, both messages, and citations
commit atomically before `201`; timeout, cancellation or failure rolls them back.
Python cannot forcibly stop an already running inference thread, but a late
answer cannot write to the request's database transaction.

Database changes require the reviewed Alembic migration described in
`migrations/README.md`. Apply it only to an approved environment. The database
table names are `conversation`, `chat_message` and `message_citation`.

## Local development fallback

`POST /api/chat/message` enables a fallback only with `APP_ENVIRONMENT=local`
(the application's local default). Healthy retrieval and inference keep using
the existing pipeline. The legacy `POST /api/chat` retains its existing behavior.

- Retrieval is allowed 5 seconds and local generation 8 seconds. On failure or
  timeout, the request tries Gemini if `GOOGLE_API_KEY` is configured in the root
  `.env`. `GEMINI_MODEL` optionally selects the model; the default is
  `gemini-3.1-flash-lite`. Gemini has a 10-second deadline, within the overall
  30-second chat budget. No extra SDK dependency is required.
- Gemini receives the retrieved context and keeps its original citations. API
  errors, quota limits, blocked/empty/malformed/truncated responses or timeouts
  fall back to a deterministic sample response.
- When retrieval itself is unavailable, fallback uses an explicitly labelled
  development fixture. Its citation has a descriptive demo title, null URL and
  null relevance score. It never invents a historical source or URL. Even when
  Gemini generates text from that fixture, the result stays labelled as a demo.
- Mock answers display `[MÔ PHỎNG DEVELOPMENT …]` and return
  `answer_type=development_mock`, `resolution_status=development_fallback`.
  Gemini with actual retrieved evidence returns `resolution_status=gemini_fallback`.
  Both paths persist the conversation, user/assistant pair and citations before
  returning `201 Created`. Mock messages store `retrieval_strategy=development_mock`.

Fallback never bypasses validation, authentication, ownership or database errors.
It is disabled in `test`, `staging` and `production`. A missing embedded GGUF
model is permitted at startup only in local mode so this endpoint can be tested.
`/api/health` still reports actual model readiness and may return `503` while
local chat successfully returns a labelled fallback.

Optional local configuration (keep the real key out of Git):

```dotenv
APP_ENVIRONMENT=local
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
```

The Gemini adapter follows the official
[generateContent REST contract](https://ai.google.dev/api/generate-content).

On Windows, Psycopg's async driver requires a selector event loop. With the
project's Uvicorn version, the recommended repository-root launch commands are:

```powershell
.\start-backend.ps1 -Port 8000
# Or, without PowerShell script execution policy requirements:
.\start-backend.bat --port 8000
```

The wrappers use the repository virtualenv or the existing parent-workspace
virtualenv. `scripts/run-backend.py` loads `.env` before API/auth imports,
honors `BACKEND_PORT` (default 8000) and selects the Windows-compatible loop.
Swagger is available at `http://127.0.0.1:8000/docs`. To run directly:

```powershell
python -m uvicorn apps.backend.app:app --host 127.0.0.1 --port 8000 --loop asyncio:SelectorEventLoop
```

This explicitly selects the compatible loop for direct local startup. Linux
can keep its usual Uvicorn command.

If registration returns `500` with `NoReferencedTableError` in the server log,
check whether the API process predates the account/role mapping update. An
existing PostgreSQL `roles` table does not register that table in SQLAlchemy
metadata. The `AdminAccount.role_id` mapping now binds directly to `AccountRole.id`.
Stop the old API process and restart with the launcher above to load that mapping;
changing `.env`, creating another roles table or re-running migrations is not
required for this stale-process error.

Registration regression tests live in `apps/backend/tests/test_auth_api.py` and
run with `python -m pytest apps/backend/tests/test_auth_api.py -v`. They use a
disposable database with real ORM flushes, Argon2 hashing and JWT authentication.
Registration normalizes email to lowercase, also checks historical mixed-case
email records and returns `400` for duplicate email/username even if another
request wins after the initial check. Database-generated account IDs replace
`MAX(id)+1`; revision `20261028_account_sequence` advances the existing sequence
past legacy manually assigned IDs without changing any account rows. Failed
writes roll back and return a safe error. Password hashing runs off the API loop.

`POST /api/auth/login` accepts exactly one of `email`, `username` or the
compatibility field `username_or_email`, plus `password`. Existing frontend
email requests retain their response contract. Email is case-insensitive;
usernames and passwords retain their case. Incorrect credentials return `401`,
including a malformed stored password hash. Inactive accounts or accounts with
a future `locked_until` return `403`; an expired lock permits normal login.
Passwords are never returned in the response/JWT. Registration requires 8 to
1024 characters and rejects all-whitespace passwords; login accepts 1 to 1024.
Reset tokens cannot be used to authenticate protected endpoints as access tokens.

## Account conversation management

All management routes require a valid JWT and an active account:

- `GET /api/chat/conversations`: own conversations only, newest activity first.
  `limit` defaults to 50 (maximum 100); `offset` defaults to 0.
- `GET /api/chat/conversations/{conversation_id}/messages`: conversation metadata
  and a `messages` array, oldest first with deterministic ID tie-breaking.
  `limit` defaults to 100 (maximum 500); `offset` defaults to 0. Each message
  includes its normalized citations, eagerly loaded without async lazy access.
- `DELETE /api/chat/conversations/{conversation_id}`: ownership checked before
  deletion; success returns `204` with no body. Database cascades remove the
  conversation's messages, citations and any associated legacy feedback.

Missing conversations return `404`. Another account's or a guest-owned
conversation returns `403`, including attempts to append through the POST
endpoint. Missing/invalid authentication returns `401` (or the existing bearer
scheme's unauthenticated status). Guest conversations never appear in an
account's list. Management routes do not open an AI/retrieval dependency.

## Automated verification

From the repository root:

```powershell
python -m pytest apps/backend/tests/test_chat_api.py apps/backend/tests/test_chat_conversation.py apps/backend/tests/test_chat_fallback.py apps/backend/tests/test_chat_integration.py -q
```

Tests use `unittest.TestCase`, `TestClient`, real JWT validation and SQLAlchemy
transactions against an isolated in-memory SQLite database. Only the AI boundary
is mocked. They cover creation/continuation, normalized citations, guest access,
ownership on read/append/delete, pagination, authentication, context validation,
both retrieval/inference timeouts, AI/storage errors and atomic rollback. A late
inference result cannot persist data after a timeout. Legacy session retention
and cascade/parent constraints are checked as well.

Fallback tests also cover Gemini request headers/payloads, dependency failures,
deadlines, demo labelling, persistence and account isolation. Gemini HTTP is
stubbed in automated tests; a real key is needed to verify its live availability.
SQLite tests do not replace PostgreSQL migration/integration verification.

`test_chat_integration.py` covers the real prompt/provider HTTP adapter, JWTs,
persistence, restoration and continuation; only retrieval and the model HTTP
response are stubbed. Empty/truncated model output is rejected, and restored
citations retain their response order. See [the task audit](CHAT_TASK_AUDIT.md)
for the latest checklist, local PostgreSQL/HTTP verification and runtime limits.
