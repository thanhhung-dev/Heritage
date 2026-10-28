# Backend Search and Chat verification — 2026-10-28

## Git synchronization

- Branch: `feat/HER-chat-backend-conversation-management`.
- Signed commit `0516fb0`: `feat: sync and test backend search and chat`.
- The checkout initially had a pending merge from `origin/develop`. Its only
  conflict was the obsolete frontend mock server, whose input datasets had
  been removed in the same merge. The conflict was resolved by removing it.
- Fetched `origin/feat/HER-search-results-ui`; latest fetched commit: `fb67f22`.
  `git merge --no-edit -S origin/feat/HER-search-results-ui` returned
  `Already up to date` because that branch was already merged by `6a4c7f8`.
- The SSH signature on the requested sync commit verified successfully.
- No push was performed.

## Local PostgreSQL migration

Target verified before execution: `127.0.0.1:5432/heritagegraph`.
Ran `python -m alembic upgrade head` from `apps/backend`.

Head is `20261028_knowledge`, following `20261028_search_sync` and `20261026_chat`.
The new revisions register 10 nullable account/tour fields and the
`knowledge_document` / `knowledge_upload` metadata tables. They preserve
existing column values and never contact R2 or modify existing Profile UUID
ownership. The initial chat migration remains unchanged.

## Test environment and fixes

Tests use the existing Python 3.11 virtualenv at `C:\Capstone 1\.venv`.
Added a reusable `apps/backend/requirements-test.txt`; CI now includes it.
Installed missing boto3, pypdf, BeautifulSoup and aiosqlite dependencies needed
by the existing test suite.

Fixed collection/import problems, the moved training configuration path,
legacy adapter filename compatibility and Windows-specific text/interpreter
fixtures. Added the existing optional GraphRAG and local-only knowledge routers
to the application. Registered the account role model required by ORM inserts.
Updated Heritage fixtures for the camera-path contract and restored optional
chat prompt history with a guard against system/developer/tool role injection.

Docker configuration tests now check the merged root Compose contract: external
services are managed by another project, so root Compose has no services or
managed database volumes. No containers were started by the test suite.
Following approval, Docker Desktop and a separate OpenSearch 3.3.0 test node
were started with `docker-compose.search-test.yaml`. It binds only
`127.0.0.1:9200`, uses a dedicated test volume and is limited to 2 GiB / 2 CPU.
Existing containers and volumes were preserved. The node reports `green` cluster
health and a healthy Docker healthcheck. See [local test instructions](opensearch-local-tests.md).

## Results and practical limits

The focused Search/Chat/RAG/ingestion suite passed: **119 tests, 37 subtests**.
It includes persisted Chat API, guest/auth/ownership cases, citations, local
fallback, Heritage API, GraphRAG boundaries and R2 administration/ingestion.

Full command:

```powershell
$env:OPENSEARCH_TEST_URL = 'http://127.0.0.1:9200'
python -m pytest apps/backend/tests/ -q --tb=short
```

Full-suite result with real OpenSearch: **187 passed, 47 subtests passed,
8 failed, 0 skipped** (40.21 seconds).
Every remaining failure is in `test_profile_consent.py`:

- `test_get_badges`
- `test_get_consent`
- `test_get_milestones`
- `test_get_profile_me`
- `test_put_consent`
- `test_put_profile_me`
- `test_put_profile_me_duplicate_handle_rejected`
- `test_put_profile_me_validation_error`

Profile/consent/gamification storage still references UUID `admin_account`
identities, while current JWT subjects refer to integer `account` IDs. Queries
fail with `uuid = integer`; Profile GET also reads a missing legacy `profiles`
table. Existing Profile data must be preserved in a separately reviewed
identity migration. Tests do not suppress or skip these failures.

The earlier six skipped `OpenSearchIntegrationTests` now all pass against the
real local node. `test_opensearch.py` reports **9 passed in 14.26 seconds**:
3 transport tests and 6 integration tests, with no skips. The integration tests
cover real indexing, lexical/vector retrieval, cosine thresholding, context
budgets, embedding model filtering and source isolation. Embedding vectors are
deterministic test fixtures; this does not measure the quality of a live BGE model.

Run the Search tests independently:

```powershell
$env:OPENSEARCH_TEST_URL = 'http://127.0.0.1:9200'
python -m pytest apps/backend/tests/test_opensearch.py -q
```

The integration fixture creates unique `heritage-test-*` indexes and removes
only those test indexes and their matching search pipelines. No test indexes or
search pipelines remained after verification.

## API smoke checks with the actual local database

Using the current FastAPI app via TestClient and the migrated Postgres database:

- `GET /api/heritages`: **200**, currently an empty published catalogue.
- `POST /api/chat/message`: **201**, persisted development mock response with
  one normalized citation. Retrieval/model services were unavailable, so this
  validates the labelled local fallback rather than live model quality.

The full Backend suite is **not yet 100% green**. The remaining issue is the
Profile identity/schema migration; its scope is awaiting confirmation.
