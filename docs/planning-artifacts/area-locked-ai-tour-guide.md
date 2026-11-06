# Area-Locked AI Tour Guide — implementation plan

Status: approved by the user (2026-11-06); code and targeted verification completed.
Rollout: pending reviewed area-tagged corpus and backend deployment; no production changes executed.
Scope: the embedded 3D tour guide, starting with Khiem Lang / Lang Tu Duc.

## Findings

- `TourChatWidget.tsx` sends structured tour/scene context through
  `scene-chat-service.ts` and `lib/scene-chat-request.mjs` to `POST /api/chat`.
- The active backend request schema accepts only message/use_rag/session_id;
  tour context is currently ignored. Retrieval has no area constraint.
- Both Hybrid branches search the full OpenSearch index. Optional Microsoft
  GraphRAG queries a global snapshot before checking passage provenance.
- The repository contains active legacy paths and corresponding refactored
  modules. Tests cover both, so area enforcement must cover both entry paths.

## API contract

Extend the existing chat DTO with `active_area_id`, bounded heritage/scene context
and bounded conversation context. Keep existing unscoped standalone chat callers
compatible. The tour widget always sends its active area.

Resolve canonical areas and aliases using server-owned definitions:
`khiem-lang` includes the tour slug `lang-tu-duc` and names Khiem Lang/Lang Tu Duc.
An invalid/unsupported area or contradictory area/tour identity must never fall
back to unrestricted retrieval. Message text cannot change the active area.

Return the resolved `active_area_id` and a separate `follow_up_questions` list.
Keep current answer/source fields. Requests about another site, including
cross-site comparisons, receive a scoped `out_of_scope` response with no foreign
citations and questions that bring the visitor back to the active area.

## Implementation milestones

1. **Area policy and search metadata**
   Add a backend area policy/registry. Propagate explicit `active_area_id` from
   trusted document/passage ingestion metadata. Preserve existing passage IDs.
   Add the keyword mapping and filter both BM25 and vector candidates before
   ranking. Recheck returned passage metadata before prompt assembly. Untagged
   legacy passages are ineligible for locked chat; titles are not proof of scope.

2. **Graph boundary**
   Add an area identity to exported GraphRAG snapshot manifests and validate it
   before querying. Locked requests may use only a snapshot explicitly belonging
   to that area, including its entities, relationships, communities and lineage.
   Without an eligible snapshot, use the already area-filtered Hybrid evidence;
   never query the global graph and filter its generated output afterwards.

3. **Answer and suggestion policy**
   Reject explicit foreign-site/comparison requests before retrieval. Qualify
   in-area follow-ups using the current tour, preserving the distinction between
   historical people and other locations. Supply the area policy separately from
   untrusted question/context text. Validate cited passage IDs and area ownership,
   and check generated answer/suggestions before returning them. No evidence
   means a scoped insufficiency response, never invented historical information.
   Initial question chips use area-specific templates without historical claims.

4. **3D widget integration**
   Derive the active area from the current tour identity; send it on every turn.
   Display the active guide scope and scoped follow-up questions. Abort pending
   requests and reset messages/draft/suggestions when the area changes so late
   responses from Khiem Lang cannot enter another tour. Scene changes within the
   same area retain the area lock. Keep existing camera/model interaction intact.

5. **Targeted verification and review**
   Test in-area questions; foreign-site questions; comparisons; alias handling;
   person-vs-place references; prompt injection; unknown/mismatched area IDs;
   both Hybrid filters; missing/wrong passage tags; wrong/global GraphRAG
   snapshots; citations; suggestions; area changes and late responses.
   Run only relevant backend tests, frontend transport tests, lint and type checks
   after implementing the approved changes. Review compatibility of both backend
   module paths. Record signed commits at meaningful implementation milestones.

## Planned code areas

- Backend: `api/chat.py`, `api/public/chat/schemas.py` and `router.py`;
  area policy in the service/domain layer; `services/passages.py` and
  `ai/retrieval/passages.py`; `core/search.py` and
  `common/search/opensearch.py`; GraphRAG adapters; answering policy/provider
  integration; ingestion metadata and `pipelines/graph/microsoft_graphrag.py`.
- Frontend: `features/chat/TourChatWidget.tsx`, `scene-chat-service.ts`,
  `lib/scene-chat-request.mjs`, overlay message/input contracts and components.
- Tests/docs: directly relevant chat/retrieval/ingestion/transport tests and API
  documentation. No unrelated Search/account functionality changes.

## Data rollout and limits

The indexed corpus needs explicit area tags, and GraphRAG needs an area-specific
snapshot before it can contribute to locked requests. Existing mixed-area
snapshots cannot prove isolation. Implementing the code does not authorize
automatic production reindexing, database migrations, deployment or model changes.
Prepare/document the required import/export steps; apply them only to an approved
environment. No new dependency or change of retrieval/inference strategy is planned.

The acceptance claim is tested scope enforcement at these application boundaries;
it does not certify the factual quality of arbitrary future model outputs.

## Implementation outcome

- Backend and 3D widget implemented on `feat/HER-area-locked-tour-guide`.
- Both legacy and refactored entry paths use the same tour policy/DTO.
- Targeted chat/retrieval/import tests: 46 passed, 6 integration skips; the extended
  GraphRAG run adds 6 passes and reproduces 4 existing failures from `fd13d62`.
- Frontend transport/scope tests: 8 passed; TypeScript and targeted ESLint passed.
- See [implementation, data preparation and verification notes](../area-locked-tour-guide.md).
