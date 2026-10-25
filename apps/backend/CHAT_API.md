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
