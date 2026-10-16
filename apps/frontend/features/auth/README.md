# Public authentication UI

## Design and route ownership

- Sign In: Figma `742:222` (Login), including populated state `744:496`.
- Sign Up: Figma `743:1054`, which contains four social buttons and no email registration form.
- `/sign-in` and `/sign-up` use the existing standalone route group, without the public navbar/footer. Thin page files compose the shared server-rendered `AuthScreen`.
- Routes, social providers and nullable Heritage policy destinations live in `config/public-auth.ts`. Existing account auth callbacks remain supported; without a callback the Guest actions navigate to these pages.

The desktop layout follows the 1920 x 1200 reference: equal 952px columns separated by 16px, a centered 470px card with a 398px control column, a light background, Inter text, and the cave image on the right. Below 1024px the form takes the full viewport and the decorative image is hidden. Short viewports scroll instead of cropping the form. Phone action buttons have at least 44px height.

On desktop viewports up to 900px high, the card uses compact vertical spacing, removes unused footer height and collapses empty validation slots. Validation text still takes its natural space when shown. The form container does not shrink, so all content remains reachable from the top when the viewport is too short or browser zoom requires scrolling. Larger viewports retain the Figma reference spacing.

## Assets and theme

The cave PNG, four 20px provider SVGs and 24px eye SVG are downloaded directly from the Figma design-context response. `auth-logo.svg` is exported intact from node `743:1058`, with outlined wordmark text, so the 103 x 20 light logo does not depend on a locally available Jano font. Assets are local under `public/figma/auth-*`; no temporary Figma URLs are used at runtime. Existing logos and other files remain unchanged.

The light auth palette uses semantic `--auth-*` tokens in `components/ThemeProvider/GlobalStyle/global.ts`, scoped to the auth screen through CSS Modules. The shared dark public shell tokens are not changed by this feature.

## Interactions and limitations

- Email/username and password are required. An identity containing `@` is checked for email shape; no arbitrary password-length policy is imposed for logging in.
- Validation messages have reserved space and accessible input associations. Password visibility is keyboard accessible, and invalid submission focuses the relevant input.
- Initial Log In is disabled until both fields are populated, matching Figma; populated submission validates locally and reports sign-in availability.
- Social buttons and Forgot password report that the action is currently unavailable. No authentication API, OAuth redirect, recovery flow, cookies, local storage or fake authenticated state is added.
- Sign In/Sign Up link to each other; the brand returns Home and Get help opens FAQ.
- Terms of Service and Privacy Policy are noninteractive until Heritage URLs are approved. The example Replit policy destinations in Figma are not copied.

Existing account/header changes in the working tree are preserved. No existing routes or components are deleted.
