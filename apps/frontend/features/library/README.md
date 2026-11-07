# Heritage Library

`/library` loads published heritage summaries using the existing `fetchHeritages` client. Search, region, language, date ordering and pagination operate on the returned array in the browser. Query parameters preserve these choices across reload and browser history. Cards link to the existing `/content/{slug}` route.

The current repository contract does not expose category or server-side pagination. These features require a confirmed backend contract; the interface does not invent category values. The hero uses the existing public background until the design image is available.

## Verification

With intercepted local API responses, checked pagination, reload and Back, region filtering, no-result and clear actions, API error and retry, empty results, card link, missing-image fallback, and visible focus. Checked horizontal overflow at 320, 375, 768, 1024, 1440 and 1920 CSS pixels, including reduced-motion mode. End-to-end verification against the deployed API remains pending while it is offline.
