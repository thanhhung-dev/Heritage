# Heritage search results

`/search` belongs to the public layout and uses its existing dark tokens and CSS Modules. No Tailwind or additional dependency is introduced.

- `useSearchUrl` owns `q`, `region`, `category`, and `page` through App Router. Only the input draft is local. Typing replaces the URL after 400 ms (paused during IME composition); submitting, filters and pagination use history navigation. Filters reset page 1, unrelated URL parameters survive, and Back/Forward restores controls. Pages above the last result page are replaced with the last valid page.
- `useHeritageSearch` owns fetching, timeout, cancellation and retry. Results from cancelled requests cannot replace a newer query. The toolbar stays mounted during loading/errors.
- `heritageSearchService` validates the API response, then filters and paginates the current small published catalogue. FastAPI currently only exposes `GET /api/heritages`; it has no server search or category field. Once a search endpoint exists, replace this adapter without changing the components. This client filtering approach is intended for the current small catalogue, not an unbounded production dataset.
- API `category` values take priority. The deployed catalogue currently omits that field, so `heritage-taxonomy.ts` supplies explicitly authored categories for its known tour slugs. Unknown/unclassified sites remain **Uncategorized**; names/descriptions are never used to guess a category. Facets come from the full response.
- Toolbar, result cards/grid, feedback and pagination have separate presentation responsibilities. Pagination uses real links. Skeletons, live status, keyboard focus, image fallbacks and reduced motion are supported.

Use the real backend at `http://localhost:8000/api` or the published catalogue below.
This feature does not silently replace API failures with mock results. The legacy
mock server and catalogue were removed by `develop`; tests use in-memory fixtures.

For the existing deployed public catalogue, the frontend configuration is:

```dotenv
NEXT_PUBLIC_API_URL=https://dev-api.worldheritagea.tech/api
```

Restart/rebuild Next.js after changing a `NEXT_PUBLIC_` setting: the public API
URL is compiled into the browser bundle. On 2026-11-06 this endpoint returned
30 published tours with working card images. Search uses those actual records;
no local database import or running local backend is required for this configuration.

All five design categories are available through the authored metadata. Region
groups list three sites initially, with **Show all** to reveal the remaining
sites; selected sites remain visible when a group is collapsed. Four result rows
are shown per page and up to five distinct catalogue recommendations remain
available even when the current search has no matches. Card images can fall back
to the same tour's splash image; the banner can try alternate catalogue imagery.

Checks from `apps/frontend`: `npm run lint`, `npx tsc --noEmit --incremental false`, `npm test`.
