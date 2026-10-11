# Public account UI (HER-163)

`PublicShell` accepts an optional `account: PublicAccount | null`. An absent account renders login and registration actions; an account renders its avatar and dropdown. HER-162 owns supplying the real session and signing out. `AccountNavigation` exposes `onSignOut` for that integration; it is disabled when no handler exists.

Login and registration are buttons only, as requested by the user. No account forms, modal, validation, or authentication requests are implemented. `AccountNavigation` accepts an optional `onAuthRequest` callback for future integration; the shared header and preview do not supply a handler yet.

Profile has no approved destination yet and remains disabled in `PUBLIC_ACCOUNT_LINKS`. Preferences links to the existing `/preferences` route. Footer destinations are nullable in `config/public-footer.ts`; unconfirmed destinations render as text, without dummy links or invented pages. Footer visibility is limited to Home, Map, Library, and FAQ.

The shared public header uses a drawer at phone widths below 768px. Tablets and desktops at 768px and above retain horizontal navigation. The drawer closes on navigation, Escape, or a resize to 768px and above. The existing `/preview` page includes a clearly labeled isolated account example for inspecting both Guest and Profile layouts without creating a fake session in the application.

Design reference: Heritage Figma, Footer `261:1855`. The account dropdown and mobile layouts are extensions authorized by the user. They reuse the installed Ant Design components, project logos, Poppins/Inter, and semantic tokens in `components/ThemeProvider/GlobalStyle/global.ts`. Footer copy and group labels follow Figma; foreground contrast is increased for readability.

The root layout places the existing `GlobalProvider` inside `<body>`. This preserves the providers and content while preventing their generated wrapper elements from creating invalid HTML directly inside `<html>` and causing hydration failures.
