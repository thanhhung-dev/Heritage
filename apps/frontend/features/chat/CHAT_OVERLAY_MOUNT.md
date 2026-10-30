# Floating chat on Tapestry scene routes

## Integration

The active route is `app/(tour)/content/[slug]/[sceneKey]`, not the public route
group. This branch did not contain the previously implemented overlay files.
The presentation, safe Markdown/citations and drag components are reused from
`feat/HER-chatbot-content-overlay` and mounted through `HeritageChatOverlay`.

The persistent content layout dynamically loads the adapter with `ssr: false`
inside `HeritageTourProvider`, after the route's children. It mounts on scene
routes independently of model readiness. The previous effect that redirected
direct scene URLs to the splash page while the engine was still loading has
been removed. Viewer readiness, camera controls and model-loading code are
unchanged; no Three.js source or fixture assets were modified.

The dock uses `pointer-events: none`; the launcher/open panel use
`pointer-events: auto`. Keyboard and wheel interactions inside chat stay within
the widget. The existing CSS Modules preserve the glass shell, draggable
launcher/header, responsive bounds, reset/resize/close actions and input behavior.
Tailwind is not installed or required. The existing locked `marked@16.4.2` is
now declared as a direct dependency for the reused safe Markdown renderer.

## API boundary on this branch

The backend currently exposes **POST `/api/chat`**, accepting
`{ "message": "...", "use_rag": true }`. The adapter uses that real contract,
normalizes origin/API-base URLs, forwards cancellation and adds a bearer token
only when present. Responses are validated before answers, sources, clarification
options or insufficient-evidence outcomes are displayed. Unsafe source links
are not clickable. No mock answers are added to production code.

`useTapestryChat` owns a 35-second request deadline, duplicate-send guard,
draft-preserving errors and cancellation on reset/unmount. Window messages remain
in memory across scene navigation and are cleared when account/heritage changes.
Quick suggestions insert the current heritage/scene names into the question.
Free-form questions are sent unchanged.

This mount does not enable account-owned persistence/history APIs: those routes
are not present in this branch. Message IDs are client rendering identifiers,
not invented server conversation UUIDs. The standalone `/chat` screen is unchanged.

## Verification — 2026-10-31

- `npm run build` passes, including Next lint/type checks and all 19 static
  pages. The two existing tour splash `<img>` warnings remain outside this fix.
- Focused chat lint and `tsc --noEmit` pass. `npm ls marked --depth=0` confirms
  the declared dependency matches the installed/locked version.
- `node --test tests/chat-request.test.mjs`: **4 tests pass**, covering the
  existing legacy contract, URL normalization, auth/cancellation and Guest mode.
- Production browser checks verify direct `/content/tapestry-test/s0` keeps its
  scene URL and exposes Ask AI before the GLB request resolves. The widget stays
  mounted after the renderer's actual ready callback and after a failed GLB.
- Native mouse dragging, open/close, scene continuity, current-tour suggestions,
  Markdown/source details, error/retry, malformed responses, abstention,
  cancelled late replies and optional Authorization pass. Canvas pointer input
  outside chat, keyboard containment, actual fullscreen and 375/320px mobile
  panel bounds pass without runtime errors.
- Browser checks use a small synthetic GLB and controlled legacy API replies,
  avoiding large asset downloads or changes to the database. They validate
  lifecycle/interaction wiring, not the production model or LLM answer quality.

Only one Next server should use this workspace's `.next` directory at a time.
After verification, the production build is served on `http://localhost:3000`.
