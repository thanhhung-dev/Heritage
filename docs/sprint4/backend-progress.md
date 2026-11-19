# Sprint 4 backend progress

Starting checkpoint: 2026-11-19, `023efa5`, `feat/sprint4-admin-auth`. Existing untracked QA files preserved. Estimates are planning references.

| Task | Estimate | Status | Implementation | Testing |
|---|---:|---|---|---|
| BE-01 | 8h | DONE | Existing admin login/logout, skipped | Previous report: isolated auth tests passed |
| BE-02 | 6h | DONE | Existing role guard/revocation, skipped | Previous report: isolated auth tests passed |
| BE-03 | 4h | DONE | Strict PATCH account status, admin guard, persisted atomic updates | Account/auth/knowledge targeted suite: 41 passed, 49 subtests |
| BE-04 | 8h | DONE | Shared current-account/version guard, versioned public/admin/Google tokens, additive SQL | Disabled login, old sessions, idempotence and reactivation verified; SQLite only |
| BE-05 | 10h | DONE | Versioned validated CRUD, history-preserving deletion, additive SQL | API/schema: 8 passed, 14 subtests; SQLite |
| BE-06 | 14h | PARTIAL | Durable scoped trigger/status and real indexing worker | Worker: 4 passed; search/ingestion/schema: 18 passed, 6 live-search tests skipped; no live external verification |
| BE-07 | 10h | TODO | Admin scene CRUD missing | Not run |
| BE-08 | 8h | TODO | Admin scene ordering missing | Not run |
| BE-09 | 8h | TODO | Admin 3D configuration API missing | Not run |
| BE-10 | 8h | TODO | Admin 3D validation missing | Not run |

Current task: BE-07/08. Next step: heritage-scoped scene CRUD and atomic reorder. BE-03/04 command: `python -m pytest apps/backend/tests/test_account_status.py apps/backend/tests/test_admin_auth.py apps/backend/tests/test_admin_knowledge.py -q`: 41 passed, 49 subtests. BE-05/06 files: `models/rag_pipeline.py`, `schemas/rag_pipeline.py`, `services/rag_pipeline.py`, `services/reindex_worker.py`, `api/admin/rag.py`, additive SQL, source-pruning adapter, extraction export and targeted tests. Windows commands now use `python -X utf8 -m pytest` because existing ingestion tests read UTF-8 artifacts using Python's default encoding; the same ingestion suite failed one hash assertion without UTF-8 mode and passed with it. SQLite cleanup after expected integrity errors was fixed in the shared fixture. No project database/migration touched.
