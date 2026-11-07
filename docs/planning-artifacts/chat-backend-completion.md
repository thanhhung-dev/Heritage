# Complete Chat Backend and Account-Based Conversation Management

Status: **implemented and verified, 2026-11-07**. The user authorized completing
missing work and continuous signed commits. See the completed
[requirement audit](../../apps/backend/CHAT_TASK_AUDIT.md) and
[API/local instructions](../../apps/backend/CHAT_API.md).

## Audit of the active branch

| Requirement | Finding before integration |
| --- | --- |
| Contracts for standalone and 3D chat | Shared transient `/api/chat`; no persisted response/history contract on this branch |
| AI answer/citation/clarification/abstention | Existing grounded pipeline and area guards work; abstention/clarification fields need explicit persistence |
| Heritage/scene and bounded history | 3D sends bounded context; standalone and saved server history are not connected |
| Account-owned persistence | Implemented on the older chat branch but absent from the active runtime |
| Conversation listing/history/delete | Not mounted in the active app |
| Ownership/guest behavior | Needs restoration and validation against current JWT/account model |
| Timeout/service/persistence errors | Area inference has timeout; whole persisted transaction and generic inference need coverage |
| Isolation/restoration/integration tests | Old branch has tests; active branch lacks them |

Local read-only inspection confirmed `127.0.0.1:5432/heritagegraph`, revision
`20261028_account_sequence`, and existing singular `conversation`, `chat_message`,
`message_citation` tables. Restore the historical migration chain without replaying
it; add an additive revision for area identity and the social-response constraint.
The user's earlier approval to migrate this specific local database still applies.

## Implementation milestones

1. Restore compatible storage/DTOs/migration lineage from the previous chat branch;
   preserve legacy session tables and extend conversation scope. Signed commit.
2. Connect transactional persistence/history/auth APIs to the current AI pipeline
   in both router paths. Preserve area locks and safe failures. Signed commit.
3. Connect both existing frontend interfaces to the finalized contract and account
   restoration without changing the approved overlay appearance. Signed commit.
4. Run isolated ORM/JWT/HTTP tests, existing chat/scope tests and local migration/
   HTTP smoke tests. Fix uncovered defects and commit the verification/report.

No wholesale merge of old AI/UI code, production changes, secret commits or new
dependency installations. Tests use isolated databases and controlled AI IO;
real-model/corpus quality is reported separately.

## Completion evidence

- Storage, canonical DTOs and migration lineage restored without replacing newer
  area-lock or approved UI code. Approved local migration is at
  `20261106_chat_scope (head)`.
- Transactional `/api/chat/message`, list/history/delete, active account and JWT
  checks, Guest policy, outcome/source restoration and rollback implemented.
- Both existing chat interfaces use the shared persisted contract and restore
  owned history, with pointers isolated by account and tour/standalone scope.
- Local fallback preserves area abstention; production failures remain explicit.
- Real Windows startup exposed an incompatible Uvicorn/psycopg event loop; the
  restored launcher explicitly selects the compatible Windows loop.
- Targeted backend verification: **91 passed + 85 subtests passed**. Frontend:
  **18 native Node tests + 3 TypeScript service tests**, TypeScript, targeted lint
  and production build passed.
- Real local Postgres/HTTP: registered and authenticated two accounts, verified
  owned persistence/history/citations, cross-account 403, Guest behavior,
  fault rollback and cascade deletion. Synthetic data and temporary server removed.
- Browser preview used actual components for both interfaces: owned ID reuse,
  restoration, account switching, Guest no-bearer and scene changes passed;
  no runtime exceptions. API/AI IO was controlled, not real-model evaluation.

No production deploy, corpus reindex or infrastructure changes were performed.
