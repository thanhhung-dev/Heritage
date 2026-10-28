# Content chatbot overlay

## Reference and access

- Figma file: `hyZGcP7zvicYLg3O7X2E2F`, requested node: Content + ChatBot.
- The authenticated REST request returned `403 Invalid token` on 2026-10-29.
  No Figma measurements were retrieved. Credentials are not stored in the repo.
- The supplied screenshots are the visual reference until working Figma access
  is available. Dimensions below are screenshot-derived targets, not measured
  Figma values; exact pixel equivalence cannot be verified from this access.
- The user explicitly approved continuing from the screenshots after the API
  access failure. No alternative credentials or private Figma URLs are retained.

## Visual direction

- A small rounded Ask AI launcher at the lower-right corner of the viewer.
- Open panel aligned to the right and vertically centered, as in the screenshots.
  Target: 360 × 580 CSS pixels with a 24px right inset, constrained by viewport.
- Frosted translucent gradient, 32px backdrop blur, subtle 15% white border and
  inset light, 24px corner radius. White text, soft grey secondary text, restrained
  orange `#f97316` interaction accent and a mint status indicator.
- Existing Poppins typography and CSS Modules with `@/` style imports.
- Compact Mila avatar/header; open space above the initial message; pale user
  bubbles; assistant text without an opaque bubble; subtle timestamps and pills.
- Reset, resize and close controls; composer anchored to the panel bottom.
  Suggestions and labels describe heritage/scene exploration rather than finance.

## Responsibilities

- `types/chatOverlay.ts`: widget, message and normalized citation contracts.
- `ChatOverlayWidget`: visibility, size, keyboard boundary and panel composition.
- `ChatToggleButton`: launcher and shared vector assistant avatar.
- `ChatMessageList`: scroll, messages, source links, suggestions and typing state.
- `ChatInputBar`: controlled input, composition-safe submit and send availability.
- A connected tour adapter will consume the existing tour context and chat service;
  presentation components do not access Three.js, authentication or HTTP directly.

## Viewer integration

`HeritageChatOverlay` mounts inside the persistent tour provider, alongside the
viewer on scene routes. It uses the current heritage/scene payload for each
message, resets on account/heritage changes and preserves the conversation during
scene navigation. The fixture route supplies descriptive context without a fake
published heritage ID. Viewer camera, playback and scene-loading code is untouched.

The overlay is non-modal: only its panel/launcher accepts pointer input. Keyboard
and wheel events stay inside the overlay while interacting with it. Escape closes
the panel and restores launcher focus. The composer supports IME, Shift+Enter,
disabled empty submissions, auto-height and a waiting indicator. Short/mobile
viewports, safe-area insets, reduced motion and missing backdrop-filter have
dedicated styles. Mobile uses a 16px composer font to prevent input zoom.

## Chat contract

- Uses the existing `POST /api/chat/message` service and optional bearer token.
- Account conversations retain their returned ID; Guest requests always create
  a new guest conversation and carry only bounded completed prompt context
  (six messages, 2000 characters per message, 6000 total). The UI greeting is
  never included. Account requests omit client history and let the server own it.
- Context is refreshed at send time when the viewer navigates to another scene.
- Normalized citations support safe HTTP(S) links and non-link source titles.
  The shared response parser retains clarification, suggestions and abstention
  fields; the overlay renders them without inventing answers or sources.
- Failed requests preserve the draft, remove the optimistic failed turn and let
  the user retry. Duplicate sends are guarded. Reset/auth/unmount abort active
  work; late results cannot update another conversation. Timeout is 35 seconds
  on the client, above the server's 30-second inference deadline.

## Verification (2026-10-29)

- `npm run build` passed with all 19 static pages generated and dynamic content
  routes compiled. Browser interaction checks were repeated on `next start` at
  port 3000, including mobile expanded height, Enter/Shift+Enter and IME input.
- TypeScript: `tsc --noEmit` passed. ESLint reports no errors in the new code;
  the full lint run retains two existing `<img>` warnings on the tour splash page.
- Chat unit tests: 14 passed across `chat-request.test.mjs` and
  `chat-service.test.ts`, including bounded Guest context and retained outcomes.
- Browser checks on the actual content route passed: launcher, greeting, draft
  retention, Enter/send guard, Escape/focus, suggestions, citations, scene
  changes, clarification, abstention, failure/retry, reset cancellation, bearer
  authentication, account isolation, resizing, mobile sizing and input font.
- Fullscreen was exercised through the real DOM API. Keyboard/wheel events from
  the composer did not propagate to the viewer's window listeners. A point
  outside the panel continued to target the viewer.
- Actual local `POST /api/chat/message` returned `201`, an answer and one
  citation, displayed by the widget. The local AI returned `development_mock`;
  the widget labelled it as a sample. Only this temporary QA Guest conversation
  was deleted afterwards using its exact ID and question.
- UI browser verification blocked large external GLB/audio/video downloads and
  used the existing fallback background; it does not validate 3D asset loading
  or live model answer quality. Controlled responses tested error/auth variants.
- Full Frontend tests: 69 passed, 1 failed. The existing lens-badge raycast test
  in `tests/tour-player.test.ts:59` expects `null` but receives `901`. Its test,
  tour sources, context, route helpers, types and dependency lockfile are
  identical to the pre-overlay commit (`91ceb1b^`). No tour engine/picking code
  was changed as part of this overlay implementation.
