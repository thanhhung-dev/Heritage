# Complete Chat Backend and Account-Based Conversation Management

Status: implementation authorized by the user's instruction to audit, complete missing work and commit continuously.

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
