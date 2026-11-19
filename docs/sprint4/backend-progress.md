# Sprint 4 backend progress

Starting checkpoint: 2026-11-19, `023efa5`, `feat/sprint4-admin-auth`. Existing untracked QA files preserved. Estimates are planning references.

| Task | Estimate | Status | Implementation | Testing |
|---|---:|---|---|---|
| BE-01 | 8h | DONE | Existing admin login/logout, skipped | Previous report: isolated auth tests passed |
| BE-02 | 6h | DONE | Existing role guard/revocation, skipped | Previous report: isolated auth tests passed |
| BE-03 | 4h | TODO | Account status endpoint missing | Not run in this session |
| BE-04 | 8h | TODO | Ordinary-session and reactivation protection missing | Not run in this session |
| BE-05 | 10h | TODO | Pipeline settings API missing | Not run |
| BE-06 | 14h | TODO | Durable reindex jobs/worker missing | Not run |
| BE-07 | 10h | TODO | Admin scene CRUD missing | Not run |
| BE-08 | 8h | TODO | Admin scene ordering missing | Not run |
| BE-09 | 8h | TODO | Admin 3D configuration API missing | Not run |
| BE-10 | 8h | TODO | Admin 3D validation missing | Not run |

Current task: BE-03/04. Next step: implement strict status updates and credential-version invalidation, then run targeted authentication/account tests. Architecture and decomposition are recorded in the adjacent documents. All new changes will be committed locally in coherent increments.
