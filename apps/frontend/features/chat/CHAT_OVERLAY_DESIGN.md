# Content chatbot overlay

## Reference and access

- Figma file: `hyZGcP7zvicYLg3O7X2E2F`, requested node: Content + ChatBot.
- The authenticated REST request returned `403 Invalid token` on 2026-10-29.
  No Figma measurements were retrieved. Credentials are not stored in the repo.
- The supplied screenshots are the primary visual reference, as confirmed by the
  user. The milestone descriptions organize implementation; their suggested
  round launcher and orange message bubbles do not override the screenshots.
  Dimensions below are screenshot-derived targets, not measured Figma values.
- The user explicitly approved continuing from the screenshots after the API
  access failure. No alternative credentials or private Figma URLs are retained.

## Visual direction

- A small rounded Ask AI launcher at the lower-right corner of the viewer.
- By default, the open panel is aligned to the right and vertically centered,
  as in the screenshots. Users can reposition the launcher and open panel.
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
- `ChatMessageList`: scroll, messages, expandable citation details and typing state.
- `ChatMarkdown`: semantic Markdown token rendering through React. Raw HTML is
  escaped, remote images are not loaded and unsafe links are not clickable.
- `ChatInputBar`: controlled four-line auto-height input, IME-safe submit,
  Shift+Enter, disabled empty submissions and four quick heritage suggestions.
- `HeritageChatOverlay` / `useChatOverlay`: current tour/auth state, request
  lifecycle, recovery, reset and restoration. Presentation components do not
  access Three.js, authentication or HTTP directly.
- `heritageChatService`: contextual facade over the shared chat service; verifies
  account and heritage metadata before restored messages reach the widget.
- `overlay-storage`: validated, bounded and account/heritage-scoped browser cache.
- `useOverlayDrag` / `overlay-position`: pointer capture, click/drag separation,
  keyboard movement, viewport bounds and launcher/panel anchoring.

## Viewer integration

`HeritageChatOverlay` is loaded with `next/dynamic` (`ssr: false`) inside the
persistent tour provider, alongside the viewer on valid scene routes. It uses
the current heritage/scene payload for each message, resets on account/heritage
changes and preserves the conversation during scene navigation. Published
heritages pass their actual ID. The preview fixture supplies descriptive context
without a fake database ID. Viewer camera, playback and scene-loading code is
untouched; the widget remains inside the document's fullscreen root.

The overlay is non-modal: only its panel/launcher accepts pointer input. Keyboard
and wheel events stay inside the overlay while interacting with it. Escape closes
the panel and restores launcher focus. The composer supports IME, Shift+Enter,
disabled empty submissions, auto-height and a waiting indicator. Short/mobile
viewports, safe-area insets, reduced motion and missing backdrop-filter have
dedicated styles. The closed panel is inert and hidden from assistive technology.
Mobile uses a 16px composer font to prevent input zoom. At widths up to 640px,
the launcher sits above the viewer's playback/menu row so both remain clickable.

## Moving the assistant

- Drag the Ask AI launcher with the primary mouse button, pen or one finger.
  Movement must reach 6px before it becomes a drag; releasing after dragging
  does not toggle chat. An ordinary click/tap still opens the assistant.
- Drag the open window by its header. Header action buttons, messages and
  the composer keep their normal behavior. Moving does not reset drafts,
  messages, the active conversation or a pending chat request.
- A moved launcher opens the panel near its bottom-right anchor, constrained
  to the screen. Closing a moved panel places the launcher at that corner.
  The original screenshot layout remains the initial default.
- Focus the launcher or header and use arrow keys to move by 10px, or
  Shift+arrow by 40px. Header buttons and textarea arrows retain their usual
  behavior. Escape closes chat and restores launcher focus.
- Positions respect a minimum 12px margin and device safe-area insets. Resize,
  orientation, panel expansion and visual viewport changes remeasure the box
  and clamp it back into view. The panel also adapts its maximum dimensions.
- Pointer cancel/lost capture, window blur and unmount release the drag.
  Touch scrolling remains available in messages and the composer; only the
  launcher/header disables native touch panning for dragging.
- Position is kept in memory during scene navigation in the current viewer.
  A full reload or account/heritage remount restores the default position.
  No new browser storage, dependency, API or viewer-engine changes are required.

## Chat contract

- Uses the existing `POST /api/chat/message` service and optional bearer token.
- Account conversations retain their returned ID; Guest requests always create
  a new guest conversation and carry only bounded completed prompt context
  (six messages, 2000 characters per message, 6000 total). The UI greeting is
  never included. Account requests omit client history and let the server own it.
- Accounts cache only a conversation UUID in localStorage, namespaced by account
  subject and heritage slug. Reopening a page fetches the owned history through
  `GET /api/chat/conversations/{id}/messages`, including pagination, citations
  and answer outcomes. Ownership remains enforced by the backend JWT; decoding
  a token subject on the client only selects a cache namespace.
- Guests keep up to 12 completed messages / 24,000 content characters in
  sessionStorage for the current tab and heritage. They never reuse a server UUID
  to read or append anonymous history. Closing the tab clears this browser cache.
- Restoring history disables sending. Missing/forbidden/deleted histories clear
  the cached UUID; transient failures show an error. Invalid authentication is
  never retried as Guest. Storage failures leave in-memory chat available.
- Context is refreshed at send time when the viewer navigates to another scene.
- Normalized citation badges open source details with safe, credential-free
  HTTP(S) links or non-link source titles and optional raw relevance scores.
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
- Chat unit tests: 24 passed across the existing `chat-request.test.mjs` (4) and
  `chat-service.test.ts` (20). Coverage includes contracts, auth, paginated
  history, outcomes, bounded context, Markdown safety, cache isolation,
  corrupt/blocked storage, restored ownership/heritage checks, drag bounds,
  reduced/shifted viewports and opening/closing near a moved anchor.
- Browser checks on the actual content route passed: launcher, greeting, draft
  retention, Enter/send guard, Escape/focus, suggestions, citations, scene
  changes, clarification, abstention, failure/retry, reset cancellation, bearer
  authentication, account isolation, resizing, 375/320px mobile sizing, four-line
  input sizing, Guest page restoration and full-page account history restoration.
- Drag-specific browser checks use native Chrome mouse/touch input: launcher
  and header dragging, movement threshold, no accidental toggle, input draft
  retention, working header actions, keyboard movement, focus restoration,
  touch cancellation/recovery, portrait/landscape/zoom bounds and scene
  continuity. Chat sending and citation rendering use a controlled API response
  in these checks, without creating new backend QA records. A separate canvas
  pointer check verifies that the area outside the widget remains interactive.
  These checks were repeated on `next start`, including dragging in actual
  fullscreen. Additional simulated device safe-area insets exercise panel size
  constraints when the available area is narrower/shorter than its default box.
- Fullscreen was exercised through the real DOM API. Keyboard/wheel events from
  the composer did not propagate to the viewer's window listeners. A point
  outside the panel continued to target the viewer.
- On the final production build, actual local `POST /api/chat/message` returned
  `201` for both Guest and JWT-authenticated account requests, with an answer and
  one citation displayed by the widget. Reloading the page restored the account's
  messages through HTTP `200`; a follow-up used the same conversation UUID.
  The local AI returned `development_mock`; the widget labelled it as a sample.
  Temporary account conversations were deleted through their authenticated API.
  The exact QA Guest record and temporary account were removed from local
  Postgres afterwards; existing user accounts/history were not modified.
- UI browser verification blocked large external GLB/audio/video downloads and
  used the existing fallback background; it does not validate 3D asset loading
  or live model answer quality. Controlled responses tested error/auth variants.
- Earlier full Frontend test run: 69 passed, 1 failed, before the additional
  Markdown/cache tests. The existing lens-badge raycast test
  in `tests/tour-player.test.ts:59` expects `null` but receives `901`. Its test,
  tour sources, context, route helpers and types are identical to the pre-overlay
  commit (`91ceb1b^`). No tour engine/picking code was changed as part of this
  overlay implementation. The focused Chat checks above pass; this document
  does not claim that the unrelated full suite is entirely green.
