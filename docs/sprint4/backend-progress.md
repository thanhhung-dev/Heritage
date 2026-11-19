# Sprint 4 backend progress

Starting checkpoint: 2026-11-19, `023efa5`, `feat/sprint4-admin-auth`. Existing untracked QA files preserved. Estimates are planning references.

| Task | Estimate | Status | Implementation | Testing |
|---|---:|---|---|---|
| BE-01 | 8h | DONE | Existing admin login/logout retained; only token generation integrated | Existing tests passed again in final regression |
| BE-02 | 6h | DONE | Existing role guard/revocation retained | Existing tests passed again in final regression |
| BE-03 | 4h | DONE | Strict PATCH account status, admin guard, persisted atomic updates | Account/auth/knowledge targeted suite: 41 passed, 49 subtests |
| BE-04 | 8h | DONE | Shared current-account/version guard, versioned public/admin/Google tokens, additive SQL | Disabled login, old sessions, idempotence and reactivation verified; SQLite only |
| BE-05 | 10h | DONE | Versioned validated CRUD, history-preserving deletion, additive SQL | HTTP/schema regression and actual PostgreSQL JSONB CRUD/migrations passed |
| BE-06 | 14h | PARTIAL | Durable trigger/status/worker; extraction now ships in backend runtime | 38 RAG tests, 3 runner guards and 5 actual PostgreSQL tests passed; real R2/BGE-M3/OpenSearch smoke still awaiting resources |
| BE-07 | 10h | DONE | Scoped metadata CRUD, parent locking and database cascades | Scene suite: 7 passed; includes rollback and ordering cases |
| BE-08 | 8h | DONE | Atomic two-phase ordering, pinned overview, stale-order conflict | SQLite swap/rollback and actual concurrent PostgreSQL test now passed during RAG follow-up |
| BE-09 | 8h | DONE | Camera/sky persisted in existing scene columns; existing viewer DTOs | 3D schema/API: 8 passed, 20 subtests; public viewer regression passed |
| BE-10 | 8h | DONE | Finite bounded vectors, safe paths, same-scene assets, valid sky references | Invalid schemas/assets/host errors and access boundaries passed |

## Initial Sprint checkpoint — 2026-11-19 (superseded by follow-up below)

Implementation and available isolated verification are finished. Final selected regression: **155 passed, 8 skipped, 133 subtests passed**, one existing Starlette/AnyIO deprecation warning. The exact command, changed-file inventory and remaining integration work are in `backend-final-report.md`. Python compilation, generated OpenAPI (35 paths, including 19 admin paths), and Git whitespace validation passed.

BE-06 and BE-08 remain PARTIAL because live dependencies/real PostgreSQL concurrency were not verified. Their code and opt-in integration tests are present. No worker continues in the background. No migration, project database change, production change, dependency installation, frontend edit, push or PR occurred. Existing untracked QA files remain excluded.

Next executable verification steps for an operator with disposable resources:

1. Set `SPRINT4_POSTGRES_TEST_URL` to `postgresql+psycopg://.../test_...` or `.../..._test`, then run `python -X utf8 -m pytest apps/backend/tests/test_sprint4_postgres.py -q`. It applies the prepared SQL only inside its random test schema and tests concurrent ordering.
2. Set `OPENSEARCH_TEST_URL` to a disposable test service and run `python -X utf8 -m pytest apps/backend/tests/test_opensearch.py -q`.
3. In a separate test deployment, apply the SQL via the approved process, configure test R2/model/OpenSearch resources, start the explicit worker, trigger a registered-source reindex and confirm COMPLETED/FAILED plus actual indexed chunks. Refresh GraphRAG snapshots separately if needed.

Earlier evidence: BE-03/04 targeted suite 41 passed/49 subtests; RAG API/schema initially 8 passed/14 subtests; worker initially 4 passed, later extended with disabled-requester coverage. Windows uses UTF-8 mode because existing ingestion tests read Vietnamese artifacts using default encoding. A default-encoding hash assertion failed and passed with UTF-8 mode. Expected SQLite integrity errors retained cursor cycles on Windows; shared fixture teardown now shields session closing and collects those cycles. Duplicate rename handling and failed final-order rollback were corrected and verified. No unresolved failure remains in the selected final suite.

## Manage RAG Pipeline follow-up — current checkpoint

Continued at the user's request after `c6c149a`. See `manage-rag-pipeline-report.md` for current evidence and `rag-completion-plan.md` for the scoped plan. The earlier final checkpoint above records the initial run; the table now includes follow-up results.

Fixed a real packaged-worker dependency problem: extraction previously imported an offline directory absent from the backend image. Shared extraction now lives in `core/document_text.py`, and existing parser pins are included in backend manifests. Actual PostgreSQL 18.4 migration/JSONB/queue/worker/concurrency tests passed in disposable databases, which were removed after use. This also closes the earlier BE-08 PostgreSQL concurrency verification gap. No application database migration/write occurred.

Current blocker: OpenSearch is not running, and torch/sentence-transformers/BGE-M3 cache are absent. Existing test-environment details were requested through the user-input tool; no answer has arrived at this checkpoint. BE-06 remains PARTIAL rather than claiming an unexecuted full-stack test passed. No installation or service start was performed. Next executable step once those explicit test resources are available: `python -X utf8 scripts/sprint4/verify_rag_postgres.py --live`. This test uses an owned temporary database/schema/index, reads only the named R2 object, and forces offline model loading. Nothing is running in the background.
