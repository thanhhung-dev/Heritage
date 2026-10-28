# Content chatbot overlay

## Reference and access

- Figma file: `hyZGcP7zvicYLg3O7X2E2F`, requested node: Content + ChatBot.
- The authenticated REST request returned `403 Invalid token` on 2026-10-29.
  No Figma measurements were retrieved. Credentials are not stored in the repo.
- The supplied screenshots are the visual reference until working Figma access
  is available. Dimensions below are screenshot-derived targets, not measured
  Figma values; exact pixel equivalence cannot be verified from this access.

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
