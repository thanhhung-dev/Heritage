# Chat API integration

`ChatExperience` subscribes to the shared authentication session. The
`useChatConversations` hook owns draft messages, pending requests, selected
conversation and paginated history. `services/chatService.ts` validates the
backend contract and adapts normalized citations for the existing Sources UI.

## Configuration and requests

Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api` in `.env.local`. A backend
origin without `/api` also works. `lib/chat-request.mjs` normalizes the base so
requests never contain `/api/api`. A relative `/api` base requires a separately
configured reverse proxy; the current Next.js configuration does not provide one.

- `POST /api/chat/message` sends `message`, nullable `conversation_id` and optional
  `heritage_context`, `scene_context`, `heritage_id`. The legacy `use_rag` field is
  not sent. Success accepts both the backend's **201 Created** and **200 OK**.
- An authenticated request sends the shared `heritage_access_token` as a Bearer
  token. Replies retain `conversation_id` for the next question.
- Guests omit Authorization and always send `conversation_id: null`. The current
  backend does not allow a guest to resume saved conversations using a UUID.
  Their visible messages remain local to the current page session.
- `GET /api/chat/conversations?limit=50&offset=…` populates the authenticated
  sidebar. Selecting an item fetches `/conversations/{id}/messages` in pages of
  500 until the complete history is loaded.
- `answer` is displayed with the response's `citations`, mapping `source_title`
  and `source_url` to the Sources component. Only HTTP(S) URLs become links.

Changing accounts or logging out resets the chat view and cancels outstanding
requests. Invalid tokens are reported as authentication errors and never retried
as a guest. API errors preserve the question for retry and display the backend's
Vietnamese detail. The browser allows 35 seconds for the backend's 30-second
inference timeout.

## Runtime prerequisites

The application database must have the approved `20261026_chat` migration from
`apps/backend/migrations/versions/20261026_01_chat_conversations.py`, including
`conversation`, `message_citation` and `chat_message.conversation_id`. Follow the
backend migration README and obtain approval before applying it to a live DB.

The configured llama.cpp service and retrieval dependencies must also be ready.
`GET http://localhost:8000/api/health` reports `503` with `model_ready: false`
when the configured model service is unavailable. With `APP_ENVIRONMENT=local`,
the persisted chat endpoint can still return `201` using its Gemini/development
mock fallback. Mock answers and demo citations are visibly labelled. See the
backend `CHAT_API.md`; an unmigrated database still prevents persistence.

## Focused checks

Run from `apps/frontend`:

```powershell
node --test tests/chat-request.test.mjs
npx tsx --test tests/chat-service.test.ts
npx tsc --noEmit --incremental false
npx eslint features/chat services/chatService.ts tests/chat-service.test.ts lib/chat-request.mjs
```

Service tests stub HTTP responses to check URL/body/auth contracts, 200/201,
history pagination, citation mapping, malformed responses and API errors. Real
AI availability must be verified separately against the running backend.
