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

The complete answer pipeline is awaited with a 30-second timeout (`504`);
inference/dependency failures return a Vietnamese `500` response. A missing DB
configuration returns `503`. The conversation, both messages, and citations
commit atomically before `201`; timeout, cancellation or failure rolls them back.
Python cannot forcibly stop an already running inference thread, but a late
answer cannot write to the request's database transaction.

Database changes require the reviewed Alembic migration described in
`migrations/README.md`. This task does not apply migrations to a live database.

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
python -m pytest apps/backend/tests/test_chat_conversation.py
```

Tests use `unittest.TestCase`, `TestClient`, real JWT validation and SQLAlchemy
transactions against an isolated in-memory SQLite database. Only the AI boundary
is mocked. They cover creation/continuation, normalized citations, guest access,
ownership on read/append/delete, pagination, authentication, context validation,
both retrieval/inference timeouts, AI/storage errors and atomic rollback. A late
inference result cannot persist data after a timeout. Legacy session retention
and cascade/parent constraints are checked as well.

SQLite tests do not replace PostgreSQL migration/integration verification. This
task renders the migration offline and does not run it on an application database.
