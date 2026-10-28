# Heritage search results

`/search` belongs to the public layout and uses its existing dark tokens and CSS Modules. No Tailwind or additional dependency is introduced.

- `useSearchUrl` owns `q`, `region`, `category`, and `page` through App Router. Only the input draft is local. Typing replaces the URL after 400 ms (paused during IME composition); submitting, filters and pagination use history navigation. Filters reset page 1, unrelated URL parameters survive, and Back/Forward restores controls. Pages above the last result page are replaced with the last valid page.
- `useHeritageSearch` owns fetching, timeout, cancellation and retry. Results from cancelled requests cannot replace a newer query. The toolbar stays mounted during loading/errors.
- `heritageSearchService` validates the API response, then filters and paginates the current small published catalogue. FastAPI currently only exposes `GET /api/heritages`; it has no server search or category field. Once a search endpoint exists, replace this adapter without changing the components. This client filtering approach is intended for the current small catalogue, not an unbounded production dataset.
- Categories are read only from an explicit optional `category` string. Missing categories appear as **Chưa phân loại**; no production labels are inferred from names or descriptions. Facets come from the full response.
- Toolbar, result cards/grid, feedback and pagination have separate presentation responsibilities. Pagination uses real links. Skeletons, live status, keyboard focus, image fallbacks and reduced motion are supported.

The existing mock API serves 30 `HeritageOut` records extended with explicit sample categories from `mocks/heritage-categories.json`. To develop without PostgreSQL, run from the repository root:

```powershell
node apps/frontend/mocks/mock-server.mjs
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8001/api` in `apps/frontend/.env.local`, restart Next.js, and open `/search`. Otherwise use the real backend at `http://localhost:8000/api`. This feature does not silently replace API failures with mock results.

Checks from `apps/frontend`: `npm run lint`, `npx tsc --noEmit --incremental false`, `npm test`.
