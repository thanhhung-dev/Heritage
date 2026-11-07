# Scene-aware tour chat suggestions

Status: implemented and verified; authorized by the user's request to code and commit scene-specific suggestions.
Branch: `feat/HER-area-locked-tour-guide` (continues the approved area lock).

## Behavior

- Derive up to four short question chips from the current story's title and
  description in `useHeritageTour`; do not hardcode content by s0/s1 index.
- Match the user's reference UI with four compact labels; keep story/heritage
  names in submitted questions and accessible descriptions, rather than extra
  visible rows. Keep `active_area_id` on every request.
- Update chips synchronously when the active story changes. Keep tour chat
  history, draft and window position. A delayed response to the old story may
  finish its existing turn, but cannot replace chips for the new story.
- Scene metadata supplies question topics, never verified historical answers.
  Handle absent metadata with area-specific questions; do not guess a story.
- No renderer/camera changes, API contract changes, dependencies or migrations.

## Milestones and verification

1. Add a pure scene-question builder and targeted tests; signed commit.
2. Wire the widget/composer to scene data and protect derived chips from delayed
   model follow-ups; targeted tests, TypeScript/ESLint; signed commit.
3. Extend story/transport regressions, document local acceptance checks, review
   staged paths for sensitive files and create a final signed commit.

## Outcome

- Scene-specific question values and guarded fallback implemented, with fixed
  reference labels following the user's UI correction.
- Widget derives suggestions from the current scene; old AI follow-up state no
  longer overwrites them. Existing conversation/window state is preserved.
- 14 targeted frontend tests, TypeScript and targeted ESLint passed.
- Edge component-preview checks passed on desktop/mobile, including changing
  scene during an outstanding mocked response. Full 3D/live-model E2E not run.
- See [local acceptance instructions](../scene-chat-suggestions.md).
