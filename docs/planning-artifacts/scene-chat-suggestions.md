# Scene-aware tour chat suggestions

Status: implementation authorized by the user's request to code and commit scene-specific suggestions.
Branch: `feat/HER-area-locked-tour-guide` (continues the approved area lock).

## Behavior

- Derive up to four short question chips from the current story's title and
  description in `useHeritageTour`; do not hardcode content by s0/s1 index.
- Show the active story beside the chips and include its title and the current
  heritage in the submitted question. Keep `active_area_id` on every request.
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
