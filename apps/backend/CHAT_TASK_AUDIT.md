# Complete Chat Backend and Account-Based Conversation Management

Validation date: **2026-11-07**. Branch: `feat/HER-area-locked-tour-guide`.

## Requirement audit

| Requirement | Completed implementation | Evidence |
| --- | --- | --- |
| Finalize both chat contracts | Shared Pydantic v2 DTOs, persisted reply/history, compatible transient API, shared FE service | Both router contract tests; both real React interfaces in browser preview |
| Existing AI pipeline; answer/citation/clarification/abstention | Current Hybrid/GraphRAG retained; validated answer outcomes and citation provenance stored/restored | Chat API, GraphRAG and conversation outcome tests |
| Heritage/scene and bounded context | Published heritage lookup, registered area lock, scene hints, six-message/6,000-character context; server history on continuation | Scope/history/context tests; s0→s3 browser request checks |
| Owned conversations and persistence | `account.id` ownership, UUID conversations/messages, normalized citations, metadata; atomic transaction | Isolated real ORM tests and real local Postgres HTTP verification |
| Listing and message history | Authenticated list/history/delete, pagination, chronological order, total count | Both router tests and real HTTP 200/204 checks |
| Isolation and Guest behavior | JWT identity, active-account checks; cross-account 403; Guest null owner with no UUID-based resume/claim | Read/append/delete isolation tests; two-account HTTP flow; frontend auth switching |
| Timeouts, services and storage errors | 30-second inference budget, rollback, safe Vietnamese errors; gated local fallback; Windows psycopg-compatible launcher | Timeout/provider/commit/cancellation checks; fallback tests; unmocked launcher smoke |
| Integration and restoration tests | Isolated SQLite + real JWT + controlled provider HTTP; real Postgres + HTTP; actual browser components | 91 pytest cases and 85 subtests pass; FE checks below |

The original active branch lacked the owned conversation runtime that existed on
an older branch. Compatible models/migrations/services were integrated into the
current pipeline instead of replacing the newer area-lock or approved UI work.

## Repeat the automated checks

From repository root:

```powershell
& "C:\Capstone 1\.venv\Scripts\python.exe" -X utf8 -m pytest `
  apps/backend/tests/test_chat_fallback.py `
  apps/backend/tests/test_chat_conversation.py `
  apps/backend/tests/test_chat_api.py `
  apps/backend/tests/test_tour_scope.py `
  apps/backend/tests/test_chat_graphrag.py -q --tb=short
```

Actual result: **91 passed, 85 subtests passed**, no failures/skips, 18.66 seconds.
One upstream Starlette/AnyIO deprecation warning remains. Tests run the same
persistence/isolation scenarios for legacy and refactored router paths. External
embedding/generation HTTP is controlled; database operations, constraints and
JWT validation are real within an isolated SQLite database.

From `apps/frontend`:

```powershell
node --test tests/conversation-storage.test.mjs tests/scene-chat-suggestions.test.mjs tests/scene-chat-request.test.mjs tests/tour-chat-scope.test.mjs tests/chat-request.test.mjs
node node_modules/tsx/dist/cli.mjs --test tests/chat-service.test.ts
npx tsc --noEmit --incremental false
node node_modules/next/dist/bin/next lint --file features/chat/TourChatWidget.tsx --file features/chat/ChatExperience.tsx --file features/chat/useConversationSession.ts --file features/chat/scene-chat-service.ts --file services/chatService.ts --file lib/conversation-storage.mjs
npm run build
```

The native Node tests passed **18/18** and TypeScript service tests **3/3**.
TypeScript and targeted ESLint passed. **`npm run build` passed**, including lint,
type checking and all 18 generated static pages. Existing nonblocking warnings
remain for optional `sharp` and two `<img>` elements on the content landing page;
no dependencies were installed or unrelated viewer code changed.

## Real local Postgres and HTTP

The explicitly approved `127.0.0.1:5432/heritagegraph` database was upgraded from
`20261028_account_sequence` to **`20261106_chat_scope (head)`**. No production schema
or infrastructure was changed. The environment venv lacks Alembic; an existing
global interpreter with the declared Alembic 1.18.4 applied the migration. No
dependencies were installed.

A temporary server on port 8014 used real registration, login, JWT validation,
SQLAlchemy and Postgres, with controlled retrieval/generation fixtures. Results:

- Two registrations 201 and logins 200; owned chats 201 with saved citations.
- Own list/history 200, restored citation records equal the original reply.
- Other-account history, append and delete each 403; list excludes the other owner.
- Resume inherits saved area; foreign-area question returns scoped abstention 201.
- Guest send 201; UUID resume 403; management without JWT 401; invalid JWT 401.
- Clarification and insufficient-evidence responses 201 with complete outcome data.
- Injected provider and commit faults 500 with no partially saved rows.
- Owner delete 204, later read 404; Postgres cascade removes its messages and
  citation records; the other owner's conversation remains readable.

All synthetic QA accounts and conversations were removed by exact identifiers.
The test server was stopped. Fixture injection existed only in temporary QA
scripts outside the repository, never in application routes.

A separate smoke test launched the **actual `scripts/run-backend.py`**, without
pipeline overrides, on port 8014. A Guest foreign-area question returned **201**,
`answer_type=out_of_scope`, correct area and no sources; exactly two rows existed
in Postgres. The test conversation was removed and the server stopped. This
confirmed the Windows event-loop fix using the real application.

## Browser integration

Edge headless ran a temporary preview containing the project's actual
`TourChatWidget`, `ChatExperience`, auth events, storage and conversation hook.
API responses were mocked in the preview; the background was illustrative.

- Approved overlay labels, welcome, placeholder and icon-only header preserved.
- Desktop 375×837 and mobile 366×732 panel sizes; no horizontal overflow.
- An s0 request completed after switching to s3 without overwriting s3 suggestions;
  the next request contained `scene_context.key=s3` and the same area.
- Guest sent no bearer token and did not reuse a Guest conversation UUID.
- Both interfaces reused owned IDs, omitted replacement client history, restored
  saved messages after remount, and isolated A/B messages after account changes.
- Standalone and tour used different stored conversation pointers.
- **Zero runtime exceptions**. Temporary preview/browser processes were closed;
  port 3000 was not started and camera/model code was not modified.

## Practical limits

This completes the eight backend requirements and their connected client
contracts. The controlled tests do **not** certify real LLM answer quality, a
reviewed area-tagged production corpus, external Gemini credentials or production
deployment. A local locked tour safely abstains when its evidence/provider is
unavailable. That is successful error handling, not a verified historical answer.

The unrelated full backend suite was not claimed green: previous audits documented
four baseline Microsoft GraphRAG route/Windows-process failures and OpenSearch
integration tests requiring a real test service. The targeted task suites above
have no such failures or skips.

## English FUT and changed files

The [English FUT workbook](../../docs/test-reports/Chat_Backend_Conversation_Management_FUT.xlsx)
follows the supplied Login template: **30 Pass, 0 Fail, 0 Not Run**. Its evidence
tab links 30 functional scenarios to 49 observed router/fallback/scope/graph test
executions. These counts summarize the wider pytest suite, not 30 additional
tests. The [report generator](../../scripts/generate-chat-fut.py) reads JUnit XML;
synthetic reporting checks confirmed failures stay Fail and absent evidence
stays Not Run. See the [reproduction steps](../../docs/test-reports/README.md).

Principal implementation files:

- Storage: `models/chat.py`, `models/admin.py`, model exports and matching
  `common/models/chat.py`; Alembic configuration, historical lineage and additive
  `20261106_06_chat_scope.py`; declared Alembic dependency.
- Backend contracts/services: `api/public/chat/schemas.py`, `schemas/chat.py`,
  `services/conversations.py`, `services/chat_context.py`, `services/chat_fallback.py`.
- API/AI integration: `api/conversations.py`, `api/chat.py`,
  `api/public/chat/router.py`, `services/tour_chat.py`,
  `ai/answering/conversation.py`, JWT exception handling in both security modules.
- Clients: `services/chatService.ts`, `features/chat/useConversationSession.ts`,
  both chat interfaces and their shared transport/storage/types/style adapters.
- Verification: conversation/fallback backend tests, client storage/service tests,
  compatibility test updates, `scripts/run-backend.py`, Windows launchers,
  English FUT generator/workbook and API/audit/area/scene documentation.

Signed implementation milestones: `a2f0537` (storage/contracts), `6084701`
(transactional API), `4fb3da4` (both clients), `21d862f` (safe local fallback),
`c3b1db5` (Windows launcher), `5f26b62` (observed English FUT).
No `.env`, `infra/`, state files or private keys are part of these commits.
