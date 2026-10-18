# HER-164: public routing and route states

## Route ownership

- Home `/`, Map `/map`, Library `/library`, and FAQ `/faq` inherit the existing public layout, account provider, header, and footer.
- Chat `/chat` and Preferences `/preferences` remain standalone.
- `/preview` and `/explore` retain their existing content and route ownership.
- `config/public-navigation.ts` owns public destinations. Navigation derives its hrefs from `PUBLIC_ROUTE_BY_KEY`; footer destinations are selected from `PUBLIC_SHELL_PATHS`.

## State boundaries

- The public route group's `loading.tsx` displays the existing `LoadingState` with a centered Ant Design spinner. Its polite, atomic status exposes the loading label without marking the live region busy; reduced motion stops rotation.
- The public route group's `error.tsx` displays `ErrorState`, keeps the public shell mounted, and calls Next.js `reset()` from the retry button. Focus returns to the persistent main content container. Exception messages and stack traces are not rendered.
- These boundaries handle content below the public layout. They do not replace error handling for the root provider, the public layout itself, standalone routes, or API requests made by a feature.
- The root `not-found.tsx` handles unmatched URLs with a standalone 404 view and a home link. It retains Next.js HTTP status handling.
- Fast or prefetched static routes may finish without displaying loading. No artificial delay or production route for simulating failure is added.

## Shared component compatibility

`LoadingState` retains `tip` and `className`. `ErrorState` retains `title`, `subTitle`, `onRetry`, and `className`, and accepts optional `retryLabel` and `headingLevel` (1, 2, or 3). The default retry label remains `Tải lại trang`. `NotFoundState` accepts an optional heading level; its default is 1.

The existing state components use CSS Modules and semantic theme variables rather than relying on unavailable Tailwind utility styles. `EmptyState` retains its exports and callbacks.

## Preview

`RouteStatesPreview` adds Loading, Error, and 404 examples to `/preview`. Retrying the error example changes only local preview state and restores focus to the resulting status. Its home link uses the real home route. Existing cards and account examples remain available.

## Verification

- ESLint, TypeScript, production build, and whitespace checks.
- Home, Map, Library, and FAQ at 320, 375, 767, 768, 820, 1024, and 1440 CSS pixels.
- Direct navigation, reload, active links, history navigation, and skip-link focus.
- Mobile drawer keyboard access, Escape and close-button focus restoration, closing after navigation, and closing on resize to desktop.
- Guest/authenticated samples, long names, profile dropdowns, and logout focus restoration. Account dropdowns close across the 768px breakpoint in both directions and focus the visible trigger.
- HTTP 404 with no public shell, and return-home navigation.
- Centered spinner, reduced motion, isolated preview retry, and browser-only error-boundary inspection with successful reset.
- Zoom at 200%, visible focus, and public-shell horizontal layout.

The browser inspection helpers and screenshots are temporary local artifacts, not production routes or additional repository test dependencies.

## Changed files (relative to apps/frontend)

| Area | Files |
| --- | --- |
| Route boundaries | `app/(public)/loading.tsx`, `app/(public)/error.tsx`, `app/not-found.tsx` |
| Shared states | `components/states/index.tsx`, `components/states/NotFoundState.tsx`, `components/states/states.module.css` |
| Route configuration | `config/public-navigation.ts`, `config/public-footer.ts` |
| Public shell | `components/public-shell/PublicShell.tsx`, `components/public-shell/PublicFooter.tsx`, `components/public-shell/PublicHeaderControls.tsx`, `components/public-shell/public-shell.module.css` |
| Theme and account | `components/ThemeProvider/GlobalStyle/global.ts`, `features/account/AccountNavigation.tsx`, `features/account/account.module.css`, `features/account/README.md` |
| Preview and documentation | `app/(public)/preview/page.tsx`, `features/route-states/RouteStatesPreview.tsx`, `features/route-states/route-states-preview.module.css`, `features/route-states/README.md` |
