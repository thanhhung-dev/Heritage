# Public account UI (HER-163 / HER-162)

`PublicAccountProvider` supplies a controlled `account: PublicAccount | null` and optional `onSignOut` callback to the public layout. `usePublicAccount` exposes the account, derived Guest/Authenticated status, and callback to header consumers. The provider defaults to Guest and does not fetch, persist, or fabricate a session. A future backend session adapter must supply the account and update it after sign-out; this presentation state is not authorization.

`PublicShell`, `PublicHeaderControls`, and `AccountNavigation` retain their optional account props. An explicit account (including null) overrides the provider. An explicit account uses its own sign-out callback rather than signing out an unrelated provider account. Without an explicit account, the header consumes the shared provider. Sign-out remains disabled when no handler exists.

Login and registration are buttons only, as requested by the user. No account forms, modal, validation, or authentication requests are implemented. `AccountNavigation` accepts an optional `onAuthRequest` callback for future integration; the shared header and preview do not supply a handler yet.

Profile has no approved destination yet and remains disabled in `PUBLIC_ACCOUNT_LINKS`. Preferences links to the existing `/preferences` route. Footer destinations are nullable in `config/public-footer.ts`; unconfirmed destinations render as text, without dummy links or invented pages. Footer visibility is limited to Home, Map, Library, and FAQ.

The shared public header uses a drawer at phone widths below 768px. Tablets and desktops at 768px and above retain horizontal navigation. The drawer closes on navigation, Escape, or a resize to 768px and above. Each header has a unique drawer ID, including preview instances. At phone widths, the account name is hidden to leave space for the avatar and hamburger; the dropdown still displays the full name. Long names truncate on desktop.

The existing `/preview` page nests an isolated controlled provider. Guest, Profile, and long-name controls update both the real `PublicHeaderControls` example and the standalone `AccountNavigation` example. Sample sign-out returns both to Guest, with focus restored to the Login button or mobile menu trigger. These sample state changes never affect the outer public header, write browser storage, or make authentication requests.

Design references: Heritage Figma, Header - User `439:1520`, ProfileJobseekerDropdown `427:2065`, and Footer `261:1855`. The account trigger reuses the dropdown's 40px circular avatar, name, and 24px open/closed chevrons. Chevron SVGs are exported to `public/figma/account-angle-{up,down}.svg` without changing their paths or dimensions. The sample recruitment labels and white dropdown theme are adapted to the approved Heritage menu and existing semantic theme; the user's avatar remains supplied dynamically rather than copying the sample portrait. Ant Design owns dropdown/keyboard behavior. Mobile layout is an authorized adaptation. Tokens live in `components/ThemeProvider/GlobalStyle/global.ts`.

The root layout places the existing `GlobalProvider` inside `<body>`. This preserves the providers and content while preventing their generated wrapper elements from creating invalid HTML directly inside `<html>` and causing hydration failures.
