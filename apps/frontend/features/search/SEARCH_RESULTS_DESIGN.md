# Heritage Search Results redesign

## Reference and implementation

The supplied Search Result and Search No Result screenshots are the visual
reference for this rebuild. Measurements are inferred from the raster images;
no editable Figma nodes or exported frame assets were supplied for these screens.
The screenshots are not embedded as application assets.

The former card grid and select-based toolbar have been removed. The new page
uses the existing Poppins typography, CSS Modules, Ant Design icons and public
navigation. Its initial desktop layout follows the reference:

- A blurred photo banner with the existing navigation above it, centered
  `HERITAGE Virtual Tours` title and supporting text.
- A full-width search field and Clear all action.
- Category Selection and grouped Location Details checkboxes in a 232px sidebar.
- Four horizontal tour rows per page, with portrait thumbnails, tour title,
  location, available languages, description, language badge and real duration.
- A centered no-results state that keeps the filters and recommendations visible.
- Five catalogue recommendations with tour links, images, titles and locations.

The shared header treatment and footer visibility are scoped to
`.shell:has([data-search-page])`, including the Suspense fallback. Other public
routes retain their existing shell. Existing navigation and account actions are
reused. Mobile uses collapsible filters, 44px checkbox label targets, a 16px
search input and a horizontally scrollable recommendation list.

## Responsibilities

| Module | Responsibility |
| --- | --- |
| `HeritageSearchPage` | Compose sections and correct out-of-range pages |
| `SearchHero`, `SearchQueryBar` | Banner and controlled query/clear actions |
| `SearchFilters` | Accessible category, region and site selections |
| `SearchResultsList`, `HeritageResultCard` | Tour rows and recommendation cards |
| `SearchPagination`, `SearchFeedback` | Page navigation, empty and retry states |
| `SearchSuggestions`, `SearchImage` | Catalogue suggestions and image recovery |
| `SearchPageSkeleton` | Complete page fallback outside the search-params boundary |
| `useSearchUrl`, `search-params` | URL parsing, navigation and debounced input |
| `useHeritageSearch`, `heritageSearchService` | Catalogue request and filtering |
| `catalogue` | Metadata facets, image validation and recommendation selection |

## URL and filtering behavior

- Query parameter `q` is debounced by 400ms. Enter submits immediately; IME
  composition waits until composition ends. Query length is limited to 200.
- Repeated `category`, `region` and `location` parameters represent checkbox
  selections. Existing single-value category/region URLs remain valid.
- Values within one group use OR; query, categories, regions and sites combine
  with AND. Matching is case/accent insensitive. Site values are heritage slugs.
- Changing any constraint resets `page` to 1. Clear all also resets pagination.
  Unrelated query parameters are preserved. Reload and browser Back/Forward
  restore the corresponding input, checkboxes and result page.
- Pagination temporarily renders disabled page controls while a query or URL
  transition is pending. This prevents navigating with an old query during
  debounce. Clear all remains available to cancel pending search constraints.
- Invalid pages become page 1. Pages beyond the filtered result count are
  replaced with the last valid page. Pagination preserves all active filters.

## API and metadata boundaries

The current backend exposes `GET /api/heritages`, a published catalogue without
server-side search/facet parameters. The adapter validates that contract with
Zod, then filters and paginates it on the client. It fetches once per mount or
explicit retry, uses `cache: no-store`, aborts on unmount and has a 15s deadline.
Changing query/filter/page does not refetch the whole catalogue.

The adapter retains real `headline`, `region`, image, `language1`, `language2`
and duration fields. Missing categories remain Uncategorized. The five category
labels from the reference remain visible; a category with no matching catalogue
metadata is disabled unless already selected, so a shared URL can be cleared.
Category is never inferred from a heritage title. Recognized Da Nang/Hue region
spellings are grouped without changing the actual location displayed on cards.

Counts come from the full catalogue, so an empty search does not erase facets.
Recommendations prefer tours outside the visible result page, are deduplicated
and capped at five. They are catalogue suggestions, not an account-based ranking.
An empty catalogue shows a truthful recommendation placeholder; no invented
production tours or historical descriptions are substituted.

Banner/card imagery uses validated catalogue URLs and the project's existing
Next Image approach (`unoptimized` for API asset hosts). Invalid or broken image
URLs fall back to a neutral image placeholder; the hero has a dark green fallback.
Tour cards link to the existing `/content/{slug}` entry route without preloading
every tour. No backend, database schema, 3D viewer or dependency changes are needed.

## Verification

Verified on 2026-10-30:

- `node node_modules/tsx/dist/cli.mjs --test tests/heritage-search.test.ts`:
  **14 passed**. Coverage includes legacy/repeated URL parameters, page reset,
  accent-insensitive matching, OR/AND selection, complete pagination,
  metadata/facet counts, unpublished exclusion, recommendations, safe image
  URLs and explicit API failure/contract validation.
- `npm run build`: **passed**, with all 19 static pages generated and `/search`
  compiled. Next's lint/type checks pass. Two existing tour splash `<img>`
  warnings and the optional `sharp` recommendation remain outside this change.
- Production browser checks on `next start`: desktop 1440×1540, mobile 375×812
  and 320×568. The result/empty screens, loaded image dimensions, result links,
  five recommendations, checkbox combinations, query debounce, IME,
  Back/Forward, reload/share links, out-of-range page correction, Clear all and
  disabled pagination during pending queries pass.
- Controlled API responses verify the loading skeleton, HTTP 503/retry,
  malformed payload errors, broken image fallback, an empty catalogue and
  recovery from unknown filters in a shared URL. Recommendation cards remain
  available when a non-empty catalogue has no matching search results.
- The responsive filter toggle, selected site filtering, horizontal carousel,
  mobile input sizing and absence of page-wide horizontal overflow pass.
- The existing FAQ header/footer were checked after leaving Search, confirming
  that the Search-specific shell styles remain scoped to this page.
- The real local `GET /api/heritages` returns HTTP **200** with **0 published
  tours**. The final page correctly renders the empty catalogue without an
  error. Populated result/recommendation checks use an isolated browser-only
  catalogue with the existing project cave image for image geometry; those
  fixtures are not part of production code or the database. No records were
  inserted, published or modified.

Run locally with `npm run dev` (or `npm run build` followed by `npm start`) in
`apps/frontend`, with the existing backend available on port 8000. Open `/search`.
Populated results require published catalogue records; category filtering
requires explicit category metadata from the API.
