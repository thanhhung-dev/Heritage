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

Progress and actual test results will be updated during implementation.
