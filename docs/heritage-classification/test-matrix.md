# Classification acceptance and regression evidence

Verified 2026-11-20 on PostgreSQL 18.4, Python 3.11 workspace venv and Node 22.16.0. Frontend manifest declares Node 24.x; CI should repeat with that declared runtime. No dependency pins were changed. Alembic 1.18.4, already pinned, was installed into the existing venv to run the actual migration checks.

## Required acceptance cases

| Requirement | Executed evidence |
|---|---|
| New heritage automatically classified | Actual INSERT, PostgreSQL trigger/outbox, worker and persisted category in `test_catalog_postgres.py` |
| Title/description changes reclassify | Actual SQL UPDATE increments revision; museum replaces prior temple categories |
| SQL/CloudBeaver detected | Direct SQL INSERT/UPDATE; unchanged update is idempotent; rollback leaves no orphan job |
| Ngũ Hành Sơn stays out of festivals | Subject definition/descriptor classifier and actual API sections in `test_heritage_classifier.py`, `test_catalog_api.py` |
| Museum does not become artifact | Museum subject with artifact mentions; artifact sections remain empty |
| Narrator does not become historical person | Actual voice/heritage_voice rows; people section remains empty |
| Multiple valid categories | Temple architecture/religion, palace history/architecture and evidenced communal building |
| Admin lock survives worker | Manual override followed by direct source update and real worker |
| No duplicate classification | Composite key, one-primary unique index, two concurrent workers and idempotent backfill |
| Draft content hidden | Draft detail returns 404; public section and authoritative source publication guards |
| No fake artifact content | Empty artifact section; no automatic marker/person/event creation; cited independent test data only |
| Existing APIs/3D maintained | Heritage/tour regression cases, frontend camera/player suite, successful Next build; old chat/RAG failures independently reproduced on baseline below |

Additional coverage: guarded backfill rollback/conflicts, stale inference after a source change, expired-lease recovery, provider fallback, semantic evidence validation, medium-confidence review gate, explicit featured eligibility/tour references, bounded query counts, actual reviewed KG evidence and withdrawal, source-backed facts, current DB admin role/status, pagination and frontend request cache/abort behavior.

## Commands and actual results

```powershell
$py='C:\Capstone 1\.venv\Scripts\python.exe'
& $py -X utf8 scripts/verify-catalog.py apps/backend/tests/test_catalog_postgres.py apps/backend/tests/test_catalog_api.py
```

**15 passed, no failures/skips, 35.60s.** The runner creates/removes an owned database, and each test uses its own schema. Fixture preparation executes the actual Alembic `upgrade()` through MigrationContext/Operations, including source/evidence triggers. The application DB is never the test target. The final additions execute the operator backfill CLI as real subprocesses (default dry-run, apply, rollback) and commit a concurrent identity/category change between two public SELECTs, proving that one response retains its repeatable-read snapshot and the next response sees the new data.

```powershell
& $py -X utf8 -m pytest apps/backend/tests/test_heritage_classifier.py apps/backend/tests/test_catalog_migration.py apps/backend/tests/test_db_init.py apps/backend/tests/test_heritage_api.py apps/backend/tests/test_tour_context.py apps/backend/tests/test_tour_scope.py apps/backend/tests/test_chat_conversation.py apps/backend/tests/test_startup_config.py apps/backend/tests/test_profile_schema_validation.py apps/backend/tests/test_p2_links.py apps/backend/tests/test_prompt.py -q --tb=short
```

**146 passed, 125 subtests, no failures/skips, 9.61s.** One existing Starlette/AnyIO deprecation warning. A narrower classifier/migration/bootstrap-contract run also passed 13 cases/12 subtests; those overlap this command and are not extra independent cases.

```powershell
# apps/frontend:
.\node_modules\.bin\tsx.cmd --test tests/catalog.test.ts
.\node_modules\.bin\tsc.cmd --noEmit --incremental false
npm.cmd run build
```

Catalog frontend: **4 passed**. Type checking passed. Targeted lint passed without warnings. Final Next.js 14.2 production build passed, generated 18 static pages and included dynamic `/catalog/[slug]`. Existing tour landing `<img>` warnings remain; no new lint warning was introduced. The first sandboxed tsx command failed at Windows `os.userInfo`; rerunning with execution permissions passed without code changes.

Alembic offline range `20261119_highlight_passage:head --sql` passed and emitted the complete SQL. Initial testing exposed use of `exec_driver_sql` against offline MockConnection; changed to documented `op.execute`, then verified both offline and actual PostgreSQL execution. `compileall`, generated OpenAPI, `pip check`, and `git diff --check` passed. No dedicated backend ruff/mypy check is configured or claimed.

## Actual processes and browser

`preview-catalog.py --fixtures --check` passed with the actual mounted application, separate production classification worker, real PostgreSQL and the existing cached BGE-M3 startup. No API/worker service was replaced by an in-memory stub. No LLM call or R2 write was needed. Its owned database was removed after the check.

A second disposable preview served explicitly labeled synthetic UI fixtures to Next dev at port 3006, overriding the frontend API URL only in that process. Edge headless CDP verified one artifact card and document scroll width no larger than viewport at **1440px** and **390px**. Screenshots were inspected; the review identified an overlarge empty hero, which was corrected before the passing final build. Screenshots outside Git:

- `C:\Capstone 1\.catalog-test-runtime\catalog-section-desktop.png`
- `C:\Capstone 1\.catalog-test-runtime\catalog-section-mobile.png`

These contain a modern application icon and clearly labeled test content, not historical artifact data. No such fixtures were inserted into the application database. The UI preview database was verified by its generated name and exact fixture slugs before removal. Children, browser and preview worktree were cleaned up.

Final cleanup checks confirmed ports **8000, 3006 and 9224 closed**, zero UI preview databases and no application catalog migration. Each integration runner also reported removal of its owned database. An execution-tool interrupt ended the interactive preview without running Python's normal cleanup message; its exact leftover fixture database was inspected, confirmed to have zero connections and removed explicitly. Normal `--check` completion did execute automatic cleanup. Screenshots and review logs remain outside Git.

## Wider baseline regressions — not a fully green repository claim

The wider backend selection returned **182 passed, 10 failures including subtests, 230 subtests passed**. All ten failing outcomes were reproduced on untouched `develop` (`0bcab82`) in a detached worktree:

- `test_heritage_graph.py`: 1 failure expecting Khiêm Lăng instead of the current Lăng Tự Đức name; baseline 1 failed/3 passed.
- `test_passages.py`: 4 subtest failures expecting `khiem-lang` instead of canonical `lang-tu-duc`; baseline 4 failed/7 passed/60 subtests.
- The deadline case in `test_chat_api.py` and outage case in `test_chat_fallback.py`: baseline 5 failures including 4 subtests, same missing scoped evidence/abstention mismatch; 1 case and 8 subtests passed.

An initial combined baseline attempt did not complete and was stopped; a captured targeted attempt timed out. They are not labeled successful. The subsequent direct, separate commands above did complete and establish the identical failing outcomes. No chat/RAG normalization, retrieval or test expectation was changed to hide them.

Full frontend `npm run test`: MJS fixture case passed; TypeScript **85 passed/7 failed**. Untouched develop reproduced exactly the same seven failing chat/scope/interactive-highlight outcomes (**81 passed/7 failed**, without the four new catalog tests). The wider suite is therefore not reported as all green. The baseline worktree was removed after checking; its dependency junction was removed without traversing the shared node_modules target.

A separate attempt to test the legacy all-ORM initializer encountered its pre-existing unresolved `user_profile -> admin_account` FK. That is documented as a bootstrap limitation, not passing migration evidence. Catalog installation uses the tested Alembic path instead.

## Data boundary

Read-only application audit: zero heritage rows and no catalog tables in the current local DB. Existing R2/media, heritage records, publication state and GraphRAG data were not changed. Actual-data backfill and rollout remain operator actions after reviewing the migration and source data. No production deployment, remote push or PR was performed.
