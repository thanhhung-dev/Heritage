# Heritage classification and artifact collection

Baseline: `develop` at `0bcab82`; implementation branch `feat/heritage-classification-artifact-collection`. User authorized end-to-end implementation, tests and frequent small local commits. No production deployment, existing media rewrite or publication-state change.

## Audit

- Mounted backend: FastAPI, SQLAlchemy async PostgreSQL, Alembic head `20261119_highlight_passage`. Existing heritage/tour APIs remain compatible.
- Homepage `app/(public)/page.tsx` explicitly includes `ngu-hanh-son` in `FESTIVAL_HERITAGE_SLUGS`, treats museum slugs as artifacts, and converts every `voice` to a heritage person. Preview groups by positional slices. These are the observed causes of misclassification.
- `heritage` is the existing tour/place source. `media_item` belongs to scenes; interactive markers have stable artifact keys but do not establish reviewed catalog/publication facts. KG `entity` serves RAG and lacks editorial publication/media/catalog fields. Reuse optional references rather than modifying graph retrieval or promoting markers automatically.
- Read-only local PostgreSQL 18.4 audit found zero heritage rows, no catalog/classification tables and a schema behind the latest marker migration. No application migration or backfill has been applied. Real production content cannot be claimed inspected from this empty local database.

## Implementation sequence

1. Define the fourteen stable taxonomy keys, entity compatibility and evidence-based deterministic engine; optional existing local LLM fallback, confidence and validation.
2. Add an editorial catalog projection for existing heritage records and independent non-place records. Add category/classification tables, relations, revisioned deduplicated durable queue and classification audit. Add transactional PostgreSQL triggers for SQL/CloudBeaver and API changes.
3. Implement leased worker/retry, admin-locked overrides and guarded backfill dry-run/apply/rollback. Never extract new historical entities merely from incidental text.
4. Expose public categories, paginated catalog/detail and mutually exclusive homepage placements; published/approved/current content with valid media only. Explicit featured selection. No LLM or knowledge-document scan in page requests.
5. Replace homepage/preview hardcoded lists, separate narrators from heritage people, add responsive artifact collection and catalog detail. Refetch visible homepage data without a stale server cache.
6. Run engine, PostgreSQL trigger/concurrency/migration, API, frontend and existing viewer/chat regressions; type/lint/build checks as configured. Document exact results and operation.

Homepage policy: individual artifacts → new collection; reviewed artifact collections → Artifacts & Treasures; people/traditions and festivals/practices get their actual entity cards; featured places/cultural experiences require explicit editorial opt-in. Each entity has one homepage placement, while retaining multiple valid taxonomy categories.

No real artifact/person/event is seeded automatically. New public non-place content requires reviewed source evidence. Uncertain classifications go to review; locked manual classifications survive worker runs. Existing records, media URLs and publish_state remain authoritative and untouched.

## Final implementation checkpoint

All seven implementation phases are complete for this branch. Scoped acceptance passed; wider pre-existing failures are explicitly recorded, not relabeled as passing. See [test-matrix.md](test-matrix.md) and [operations.md](operations.md) for executed commands, remaining rollout work and manual verification.

| Phase | Result |
|---|---|
| Audit | Root causes traced to homepage slug lists, narrator promotion and positional preview slicing; local data availability checked read-only |
| Database | Additive Alembic revision with six editorial tables, fourteen categories, constraints/indexes and four transactional triggers |
| Engine | Subject-first deterministic rules, reviewed linked identity evidence, opt-in bounded llama proposals, confidence/review, lease/retry worker and audited backfill/rollback |
| Backend | Public taxonomy/catalog/sections/detail, strict independent entity creation, current-account admin checks, locked overrides, retry/status and sourced relations |
| Frontend | API-only homepage/preview, server-ranked hero, exclusive placements, sourced artifact collection/detail, pagination, periodic cache-free refresh and honest empty states |
| Testing | 15 PostgreSQL/API tests, 146 selected backend tests and 4 catalog frontend tests passed; type/lint/production build and desktop/mobile browser checks passed |
| Report | Operator runbook, API/placement policy, data boundaries, exact evidence and baseline failures documented |

Primary files: `models/heritage_classification.py`, `migrations/versions/20261120_09_heritage_classification.{py,sql}`, `services/heritage_taxonomy.py`, `heritage_classifier.py`, `classification_{input,semantic,store,worker,backfill}.py`, `services/catalog.py`, `schemas/catalog.py`, `api/catalog.py`, `api/admin_catalog.py`, public homepage/preview/catalog routes and their home/catalog components. The legacy initializer excludes trigger-managed catalog tables, preventing bare ORM tables from blocking the migration. Compose has an opt-in worker profile.

No request requires paid AI, no SQL trigger calls a model, and no public render request scans documents or invokes classification. Admin locks survive source changes and worker runs. Taxonomy is independent of UI sections, region and publication state. Multi-category membership is preserved while homepage placement is exclusive. New artifact/person/event/practice records need explicit sourced editorial input; marker media and narrator rows are never auto-promoted.

Public catalog requests use one read-only repeatable-read snapshot so concurrent worker commits cannot mix an entity with different category rows or duplicate its placement across sections in the same response. The admin write-session dependency remains separate. The final PostgreSQL test commits such a change between the entity and category queries, then verifies both the stable first response and the updated next response.

Rollout remains separate: the current application DB has no heritage data, so no real dataset was backfilled and no live-site classification accuracy is claimed. Migrations/backfill must be reviewed and applied to the intended dev/staging/production target by the operator. No source heritage row, media URL, publication state, RAG strategy or remote branch was changed by this implementation run.

## UI follow-up — shared English carousel

At the user's request, Heritage Artifacts Collection now renders through the same `HeritageCarouselSection` as the other homepage sections. Its separate grid, copper background and custom state boxes were removed. Header typography, diamond icon, image backdrop, portrait cards, arrow controls, loading, empty and error states now share the existing implementation. In particular, an unavailable collection displays one error notice rather than an error plus an empty-state box.

Homepage descriptions, controls, status messages and accessibility labels are English. Artifact fact labels, the information dialog and catalog detail interface are English too. Stored titles, descriptions, media and source citations are preserved. Sourced facts remain available in the dialog/detail through `features/catalog/ArtifactFacts.tsx`.

Verification: four existing catalog frontend tests passed; TypeScript and targeted lint passed; the production build passed with only the two existing tour-page image warnings. Edge headless checked cards/empty/error at 1440px and 390px: matching shared section classes, two arrow controls, no page overflow, working right-arrow scrolling, English fact/source labels in the information dialog, and exactly one error notice without an empty state. This presentation check used a separate local fixture API, not production data. Its API, frontend and browser were stopped and ports 18926/3006/9225 confirmed closed.
