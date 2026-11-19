# Khoa backend re-audit — 2026-11-20

Requested scope: independently re-read and verify all ten backend tasks from the Sprint 4 assignment and supplied task table. Preserve unrelated QA files and frontend work. Commit each coherent correction or verification increment locally; no push or deployment.

Baseline: `28c2d49`, branch `feat/sprint4-admin-auth`. The earlier DONE labels are previous evidence, not a substitute for this audit.

| Tasks | Review and verification | Current audit |
|---|---|---|
| BE-01/02 | Login/logout, token lifetime, revocation aliases, current database role; all admin guards | Reviewing |
| BE-03/04 | Strict account status, disabled login/session, reactivation, concurrent status changes | Reviewing |
| BE-05/06 | Config CRUD/revisions, scope, queue claims, failure handling, real R2/model/search/DB | Reviewing |
| BE-07/08 | Heritage association, CRUD/cascades, pagination, full ordering, concurrent writes | Reviewing |
| BE-09/10 | Camera/environment persistence, vector/path validation, asset ownership, public viewer | Reviewing |

Execution: inspect production paths and current tests; run the selected backend regression; reproduce and fix any defects with regression coverage; strengthen missing real-PostgreSQL checks; rerun the real RAG integration; record exact results and provide a Vietnamese manual test guide using disposable development resources.

The “Manage Knowledge” rows assigned to Khoa concern account activation/deactivation. Admin action history and heritage CRUD belong to Hùng and are outside this audit.

Results will be appended only after commands complete.
