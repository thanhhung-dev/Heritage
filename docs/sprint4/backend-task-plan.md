# Sprint 4 task plan

User authorized autonomous implementation and frequent local commits; completed work is skipped. No push, PR, deployment, dependency upgrade or production migration. Estimates remain the original 84h planning reference, not actual elapsed effort. Subtasks are <=8h; BE-01/02 reuse earlier implementation. Execution follows auth/status, RAG, scenes, then 3D.

| ID | Module | Subtask | Estimate | Dependencies | Status |
|---|---|---|---:|---|---|
| BE-01.1 | Auth | Existing admin login/token issuance; valid/invalid credential tests | 5h | None | DONE |
| BE-01.2 | Auth | Existing logout and response contract tests | 3h | BE-01.1 | DONE |
| BE-02.1 | Auth | Existing DB admin enforcement across admin routes | 3h | BE-01.1 | DONE |
| BE-02.2 | Auth | Existing persistent logout revocation and reuse tests | 3h | BE-01.2 | DONE |
| BE-03.1 | Accounts | Strict status update, persisted state, admin scope and HTTP tests | 4h | BE-02.1 | DONE |
| BE-04.1 | Accounts | Credential version migration and current-account guard | 4h | BE-03.1 | DONE |
| BE-04.2 | Accounts | Login/reactivation/session regression tests | 4h | BE-04.1 | DONE |
| BE-05.1 | RAG | Validated persisted chunking/embedding/retrieval DTO/model/migration | 5h | BE-02.1 | DONE |
| BE-05.2 | RAG | Admin CRUD, conflicts, docs and HTTP tests | 5h | BE-05.1 | DONE |
| BE-06.1 | RAG | Scoped durable job trigger/status and duplicate protection | 6h | BE-05.2 | DONE |
| BE-06.2 | RAG | Worker, actual indexing integration, failure/recovery tests | 8h | BE-06.1 | DONE |
| BE-07.1 | Scenes | Heritage-scoped CRUD DTO/service/router | 6h | BE-02.1 | DONE |
| BE-07.2 | Scenes | Association, deletion and authorization tests/docs | 4h | BE-07.1 | DONE |
| BE-08.1 | Scenes | Parent lock, temporary sequences, optimistic stale-order check | 5h | BE-07.1 | DONE |
| BE-08.2 | Scenes | Duplicate/missing/cross-heritage/order consistency tests | 3h | BE-08.1 | DONE |
| BE-09.1 | 3D | Store/read camera and existing sky/asset DTOs | 5h | BE-07.1 | DONE |
| BE-09.2 | 3D | Viewer compatibility and persistence tests/docs | 3h | BE-09.1 | DONE |
| BE-10.1 | 3D | Strict vectors, bounded values, trusted asset paths and associations | 5h | BE-09.1 | DONE |
| BE-10.2 | 3D | Invalid schemas/assets and unauthorized access tests | 3h | BE-10.1 | DONE |

Acceptance: each subtask's described behavior must be implemented, have meaningful passing tests, and appear in the API contract/progress report. Schema additions are prepared as SQL migrations only. Unit/SQLite tests are distinguished from live integration tests; infrastructure-dependent verification cannot be marked complete without evidence.

Final dependency note: renewed user authorization allowed actual cloud verification to run. BE-06.2 passed with real R2, the pinned BGE-M3, actual OpenSearch and PostgreSQL; the job reached COMPLETED and its indexed vector was verified. The cloud command passed all six selected cases without skips. Every subtask above is DONE. Killed-worker manual reconciliation and separate immutable GraphRAG snapshot maintenance remain documented behavior. Prepared SQL was applied only inside owned temporary test schemas, never the application database. All owned test cloud/database/search artifacts were cleaned up and the search process stopped. Estimates remain 84h with no invented actual effort. Operator deployment is separate from the completed implementation/acceptance work.
