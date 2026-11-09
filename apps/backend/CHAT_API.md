# Chat API and local verification

Verified on 2026-11-07. The standalone chat and 3D overlay use the same persisted
contract. API routers are thin adapters around `services/conversations.py`; both
legacy and refactored router paths mount `api/conversations.py`.

## Endpoints

| Method and route | Authentication | Success |
| --- | --- | --- |
| `POST /api/chat/message` | Optional access JWT | 201, committed user/assistant pair |
| `GET /api/chat/conversations?limit=50&offset=0` | Required access JWT | 200, own conversations ordered by latest update |
| `GET /api/chat/conversations/{id}/messages?limit=100&offset=0` | Required access JWT | 200, chronological messages and `total_messages` |
| `DELETE /api/chat/conversations/{id}` | Required access JWT | 204, messages and citations cascade |

List limits are 1–100; history limits are 1–500. Offset must be nonnegative.
`POST /api/chat` remains available as the legacy transient contract; it does not
save history. New clients use `/api/chat/message`.

## Request and response

```json
{
  "message": "Giới thiệu câu chuyện đang xem tại Khiêm Lăng.",
  "conversation_id": null,
  "active_area_id": "khiem-lang",
  "heritage_context": {"slug": "lang-tu-duc"},
  "scene_context": {"key": "s0", "title": "Hòa Khiêm Điện"},
  "conversation_context": []
}
```

Only `message` is required for standalone chat. Optional `heritage_id` must refer
to a published heritage; its server-side slug must match the selected area.
Structured heritage/scene context requires a registered `active_area_id`; a
heritage-context slug must match it. Bounded strings are accepted as legacy hints.
Hints and history are user data, never historical evidence or system instructions.

Messages must contain 1–8,000 characters after trimming. Client context contains
at most six user/assistant messages, 2,000 characters each, 6,000 total. Each
heritage/scene context is limited to 2,000 serialized characters. Invalid request
fields, UUIDs or unsupported roles return 422.

### Optional tour companion context

The tour client additionally sends `heritage_id` and a bounded `tour_context`:

```json
{
  "message": "Kể thêm về điểm đang chọn.",
  "active_area_id": "khiem-lang",
  "heritage_id": 1,
  "tour_context": {
    "scene_id": 3,
    "mode": "standard",
    "highlight_id": 4,
    "story_id": null,
    "completed_story_ids": [],
    "narration": "partial"
  }
}
```

IDs above illustrate the inspected development payload, not stable seed data.
The server validates published heritage → scene → interaction/highlight ownership
and the interaction's mode against SQL data before retrieval. Client labels are
not authoritative. Mode is `scene`, `standard`, `free`, or `walk`; a highlight is
invalid in `scene`. Narration is `unavailable`, `not_started`, `partial`,
`completed`, or `skipped`, and is a UI hint, not historical evidence.

`completed_story_ids` contains at most 32 IDs, each 1–80 characters. A requested
`story_id` must match an editorial branch for the resolved scene/point and its
exact question. Each branch requires its reviewed passage IDs both in retrieved
evidence and in the answer's citations. Invalid relations or branch requests
return 422; unavailable identity storage returns 503. Requests without
`tour_context` retain their existing contract.

Responses and saved assistant history include optional `reply_context`:
`scene_id`, canonical `scene_key`/`scene_title`, `mode`, `highlight_id`/
`highlight_title`, and `story_id`. Non-answered replies clear `story_id`; local
scoped service-unavailable replies retain validated scene/point identity. New
tour-context replies do not include generated follow-up questions. Old messages
without metadata remain unlabeled, never assigned the current scene.

The single-load heritage/tour payload adds optional-default-empty `guide_stories`
to scenes and interactive highlights. The registry is currently empty: no
Khiêm Lăng historical branch has approved independent sources. See
[`docs/tour-guide-mvp.md`](../../docs/tour-guide-mvp.md) for the pilot audit,
session lifecycle, verification evidence, and remaining acceptance gates.

The 201 response includes:

- `conversation_id`, `message_id`, `answer`.
- `sources`: the selected original passage metadata for existing UI clients.
- `citations`: normalized records with `id`, `message_id`, `source_title`,
  `source_url`, `relevance_score`. Unsafe URLs and nonfinite scores are removed.
- `answer_type`, `needs_user_choice`, `clarification_question`, `suggestions`.
- `abstained`, `abstention_reason`, `active_area_id`, `follow_up_questions`.
- Existing correction/entity/intent/resolution fields.

`answered` requires retrieved citations. `conversation` covers nonfactual social
replies without invented citations. Clarification asks a safe question and does
not invent evidence. `insufficient_evidence` and `out_of_scope` set `abstained`;
service outages in a local locked tour use `abstention_reason=service_unavailable`.
History returns these outcomes, the original sources and normalized citations,
including their original order, with every stored message.

## Ownership, Guest and continuation

Signed-in requests send `Authorization: Bearer <access_token>`. Ownership comes
from the verified JWT subject and active account record. Client-supplied account
IDs are not accepted. Invalid, expired, wrong-purpose or malformed supplied
credentials are rejected with 401, rather than silently becoming Guest requests.

Guest requests omit Authorization. A new conversation is saved with a null owner,
but its UUID grants no read, append, delete or claim permission. A subsequent
Guest turn starts a new record and may send bounded client context. The Guest UI
retains its visible conversation only in memory. Signing in starts an owned
conversation; it does not claim any Guest record.

Owners resume by sending `conversation_id`. The server supplies bounded history
from the database and rejects replacement client history with 400. The persisted
area is inherited if omitted; switching or removing its scope is rejected. Open
a new conversation when switching tours. Another account receives 403 for read,
append and delete; an unknown UUID returns 404. Management without a JWT returns
401. Accounts that have been disabled or deleted cannot use saved chat.

Frontend pointers are saved per account and tour/standalone scope. Both interfaces
restore owned messages through the history API. A new-conversation action clears
the pointer; it does not delete existing database history. Auth changes unmount
the old conversation state and abort pending requests.

## AI, transaction and failures

The existing Hybrid/GraphRAG pipeline remains in use. Area-locked requests keep
retrieval filters, area-only graph snapshots, source validation and safe follow-up
questions. Scene changes supply current story labels while retaining the same
area-owned conversation. Assistant history is never accepted as source evidence.

Inference is bounded by `asyncio.wait_for(..., 30)`. Both messages and all citations
commit in one transaction before a 201 response. Timeout, cancellation, provider
failure, invalid output and persistence errors roll back partial turns. A row
lock serializes continuation/deletion of the same conversation.

| Failure | Persisted API result |
| --- | --- |
| Inference timeout, fallback disabled | 504 with safe Vietnamese detail |
| Provider/generation failure, fallback disabled | 500 with safe Vietnamese detail |
| Database transaction failure | 500 with safe Vietnamese detail |
| Database unconfigured | 503 |
| Ownership mismatch | 403 |
| Invalid credentials or missing required credentials | 401 |
| Inconsistent saved scope or replacement history | 400 |

Local fallback is enabled only with `APP_ENVIRONMENT=local` and
`CHAT_DEVELOPMENT_FALLBACK=true` (local default). Local primary inference has an
8-second budget within the outer 30-second limit. Standalone chat can try Gemini
through `GOOGLE_API_KEY`; if unavailable, it returns a clearly labeled Development
mock. It uses actual retrieved sources where available and a clearly labeled demo
source otherwise. It never invents a public source URL. Locked tours abstain on
outage without calling general Gemini or attaching demo/foreign citations.
Production/test/staging do not enable this fallback. Setting
`CHAT_DEVELOPMENT_FALLBACK=false` enables strict failure testing locally.

## Run on Windows

From repository root, with the project's existing Python environment:

```powershell
.\start-backend.ps1 -Port 8000
# Equivalent:
& "C:\Capstone 1\.venv\Scripts\python.exe" scripts/run-backend.py --port 8000
```

The launcher loads `.env` before security/API imports and explicitly uses
`asyncio:SelectorEventLoop` on Windows, which psycopg async requires. Direct
Uvicorn startup can choose the incompatible Windows Proactor loop.

The approved local `heritagegraph` migration was applied successfully; current
head is `20261106_chat_scope`. The compatible existing tables are singular
`conversation`, `chat_message`, `message_citation`, with ownership referencing
`account.id`. Do not create parallel plural tables or run `create_all()` in
production. Migration tooling must already exist in the selected interpreter:

```powershell
python -X utf8 -m alembic -c apps/backend/alembic.ini current
# Only against an explicitly approved target database:
python -X utf8 -m alembic -c apps/backend/alembic.ini upgrade head
```

Open `http://localhost:8000/docs`. Register/login two test accounts, authorize as
A, create a message and record its conversation UUID. Read the list/history,
append a turn, then authorize as B and confirm read/append/delete of A's UUID
return 403. Delete as A: 204, followed by 404; verify B's conversation still exists.
Without authorization, send a new Guest message (201), then confirm its UUID
cannot be resumed (403) and management requires login (401).

See [the completed audit](CHAT_TASK_AUDIT.md) for executable commands, exact test
results and the distinction between controlled AI IO and real-model evaluation.
