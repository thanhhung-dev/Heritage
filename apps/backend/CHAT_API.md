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
| `GET /api/admin/interactive-highlights/{id}/passages` | Admin JWT | 200, reviewed links |
| `POST /api/admin/interactive-highlights/{id}/passages` | Admin JWT | 201, link one existing OpenSearch passage |
| `DELETE /api/admin/interactive-highlights/{id}/passages?passage_id=...` | Admin JWT | 204, unlink one passage |

List limits are 1–100; history limits are 1–500. Offset must be nonnegative.
`POST /api/chat` remains available as the legacy transient contract; it does not
save history. New clients use `/api/chat/message`.

## Request and response

```json
{
  "message": "Giới thiệu câu chuyện đang xem tại Khiêm Lăng.",
  "conversation_id": null,
  "active_area_id": "lang-tu-duc",
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

Tour requests may include `recent_suggestions`, an optional list of up to six
previously displayed questions (1–200 characters each). Older clients may omit
it. This hint only reduces repeated suggestions; it is not evidence or a signal
of a lasting user preference. The existing `follow_up_questions` response field
contains zero to two suggestions for tour answers. A separate model pass considers
the current question, answer, bounded dialogue, recent suggestions and retrieved
evidence. It suppresses suggestions for correction/closing intent, filters
unsupported, already answered or repeated candidates, then ranks relevance,
novelty and diversity. Semantic judgments are model estimates, not independent
proof of answerability. Invalid or timed-out planning returns an empty list and
preserves the answer; raw-source fallback, social, recall and out-of-scope replies
do not launch this pass. No schema migration or additional retrieval is involved.
The UI displays suggestions only for the latest assistant reply. The client does
not currently distinguish a suggestion click from an identical typed question.
Optional planning uses the cancellable `llama_server` backend, at most three
candidates and a 12-second budget within the chat deadline. The in-process
`llama_cpp` backend skips this optional pass. Legacy unscoped chat with no evidence
returns `insufficient_evidence`; scoped Tavily research remains in the tour service.

Messages must contain 1–8,000 characters after trimming. Client context contains
at most six user/assistant messages, 2,000 characters each, 6,000 total. Each
heritage/scene context is limited to 2,000 serialized characters. Invalid request
fields, UUIDs or unsupported roles return 422.

Saved conversations still load that bound from PostgreSQL. When `REDIS_HOST` is
set, the context worker prepares the same bound after each committed turn. The
next turn uses the snapshot only if `through_message_id` is still the latest
saved message. A miss, a stale snapshot, or a Redis error reads PostgreSQL and
does not change the answer contract. The snapshot is user history, not evidence.

Questions about this conversation are answered from the saved user and assistant
turns. Those turns are not historical evidence. The model must use
`answer_type=conversation` and no sources for them; the server keeps that answer
instead of treating it as out of scope. Heritage facts still require passages.

### Optional tour companion context

The tour client additionally sends `heritage_id` and a bounded `tour_context`:

```json
{
  "message": "Kể thêm về điểm đang chọn.",
  "active_area_id": "lang-tu-duc",
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
scoped service-unavailable replies retain validated scene/point identity. Tour
replies return up to three server-filtered follow-up questions for the active
area or verified artifact. Old messages without metadata remain unlabeled.

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

Area scope is enforced by `active_area_id` metadata, not a blacklist of place
names. A passage about the active site may mention another place; related
questions may use it when it actually supports the answer. Explicit requests
for another registered tour are generated as normal `out_of_scope` chat
responses with no sources. The server permits the destination name only for
navigation and falls back to safe wording if the model cites evidence, emits
links/source labels, dates, or historical claims in that response.

An area-locked tour turn normally makes one structured generation call, including
greetings and explicit out-of-scope questions. A selected badge with no reviewed
links or no usable linked evidence abstains without invoking the model.
The internal JSON contains `answer_type`, `answer`, `source_ids` and optional
`follow_up_questions`. `answered` still requires citations belonging to the
bounded active-area Passages. A partially supported answer remains `answered`:
it states that the requested detail is unverified, then may present only the
related fact supported by its citation. Other outcomes cannot attach citations.
Invalid JSON, invalid citations and unsafe scope output are discarded. A factual
turn without a citation that belongs to the retrieved passages abstains; raw passage text is not returned as the answer.
Retrieval/context service failures retain their HTTP
errors; the total request deadline remains unchanged.

Bounded user/assistant turns are retained in the generation prompt to resolve
pronouns, omitted subjects and confirmation questions; they are not historical
evidence. Server-validated scene/highlight titles identify what the visitor is
viewing. Passage labels remain attached to their text so the model can assign
source IDs correctly. Rejected tour answers log a reason category without user
text or model output; they return `insufficient_evidence` with no sources instead
of a raw passage dump. The response contract remains unchanged.
For referential turns the retrieval query includes bounded prior user topics.
There is no separate rewrite generation in a locked tour. Standalone chat keeps
its existing rewrite behavior and may still use two model calls.

P2 applies to a server-validated `(active_area_id, scene_id, mode, highlight_id)`.
PostgreSQL `interactive_highlight_passage` stores each reviewed pair of badge ID
and OpenSearch `_id`, plus the SHA-256 content hash and source `object_key`/`bucket`
at review time. One passage may be linked to multiple badges. An admin supplies
the actual passage ID to the link endpoint; the backend reads the passage and
checks its text hash and area before committing the link. It does not infer a
link from popup labels. Duplicate labels therefore cannot grant access to a
different badge's sources. Admin listing and unlinking do not modify the corpus.

After badge selection, chat retrieves using the existing hybrid ranking but
restricts both OpenSearch branches to the linked IDs and current area. It checks
the returned `_id`, area, current text hash and source provenance again; only
verified chunks (including GraphRAG lineage) can reach the prompt or citations.
The selected point's short title is a reference hint, not evidence. No links,
stale/changed passages, or no relevant linked evidence yields
`insufficient_evidence`, without a general area fallback. Deselecting the badge
returns to P1 area retrieval. `artifact_key` remains in the existing database
and admin edit API but is not used for P2 retrieval. The link map is never
included in chat responses or saved `reply_context`.

The new Alembic migration is supplied but has **not** been applied to a real
database; no real passage links have been entered or audited. Existing badges
will not have P2 evidence until an admin reviews and links their actual passages.
Reimported passages with changed IDs, text hashes or provenance require review
again. Citation checks still apply; source locking alone cannot guarantee every
claim in generated text is correct.

Chat inference is bounded by `CHAT_TIMEOUT_SECONDS` (default **120 seconds**),
shared by `/api/chat`, `/api/chat/message` and area-locked tour generation in both
router paths. Set it in the backend environment to a finite positive number of
seconds; invalid values fail startup. This is the total retrieval and
answer-generation budget, not an additional budget for each phase.
`LLAMA_SERVER_TIMEOUT` remains the separate upstream HTTP timeout; increasing it
alone does not extend the chat deadline. A 504 detail reports the configured
chat limit rather than a hard-coded 30 seconds.

The backend initializes BGE-M3 and encodes a short warmup query in its lifespan
before accepting requests. First-start imports/model loading therefore do not
consume the first user's chat deadline. Startup can take longer on a cold cache;
wait for `Query embedding model ready` and Uvicorn's startup-complete log before
sending chat requests. Embedding initialization failure fails startup and releases
database/tracing resources instead of reporting a ready API with a cold model.

Both messages and all citations commit in one transaction before a 201 response.
Timeout, cancellation, provider failure, invalid output and persistence errors
roll back partial turns. A row lock serializes continuation/deletion of the same
conversation.

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
8-second budget within the configured outer chat limit (120 seconds by default).
Standalone chat can try Gemini through `GOOGLE_API_KEY`; if unavailable, it returns a clearly labeled Development
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

The previously approved local `heritagegraph` chat-scope migration was applied;
that verification recorded `20261106_chat_scope`. The new
`20261119_highlight_passage` migration has not been run. The compatible existing
tables are singular `conversation`, `chat_message`, `message_citation`, with ownership referencing
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
