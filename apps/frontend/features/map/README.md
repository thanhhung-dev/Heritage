# HeritageGraph regional 3D map

`/map` renders Huế and post-2025 Đà Nẵng (including former Quảng Nam) using a
native React client host and one Three.js renderer. The exception to the repo's
React Three Fiber preference was explicitly approved for this feature.

## Ownership

- `geography.ts`: boundary validation, geographic membership and shared projection.
- `classic-scene.ts`: adapted classic geometry, materials, side gradient, contour
  chase ribbon and HUD ring. Each original polygon/hole is retained. Decorative
  normal-mapped relief does not displace boundary vertices away from side walls.
- `map-engine.ts`: owns one scene/camera, gesture controls, animation loop and
  disposal. Only the mainland presentation (including nearby islands) is shown.
  Polygons east of 110°E are not rendered; source coordinates remain unchanged.
- `HeritageMap.tsx`: native React 18 lifecycle and accessible canvas description.
- The route owns API requests, data/error/retry states, an expandable heritage
  list and the existing shared PortraitCard. There is no new backend/API dependency.

The layout places the selected card, statistics and expandable list to the left
of the unframed canvas. On mobile the canvas remains 3D and precedes the sidebar.
Glowing orange marker buttons follow heritage coordinates through orbit and
zoom, alongside floating zoom-in/out and whole-region reset controls. The Hoàng
Sa inset remains hidden. Drag to rotate; scroll or pinch to zoom. Both marker
and list selection open the card and center/zoom the camera to that heritage
with a 700ms eased flight (instant for reduced motion). User gestures, zoom and
reset cancel a flight; reset restores the fitted whole-region orientation and
zoom. Closing a card or pressing Escape restores focus to its marker/list
button, or the list summary if collapsed. The list also provides access to
nearby overlapping markers without moving geographic coordinates. Map errors
retain an accessible retry action, not a simulated fallback map.

`MAP_THEME_PRIMARY` uses the project's orange `#ff9b2d` for renderer materials.
The route stylesheet uses existing global background, text and accent tokens;
no site-wide theme or shared card styles were changed.

## Source attribution and license

Based on three-scope-map-skill by 宋夏天Dazzle.
作者全平台ID：宋夏天Dazzle；公众号：送你整个夏天
Original repository: https://github.com/songsummer920-dazzle/three-scope-map-skill
Pinned revision: `f8c93697c010801e203c9b9f49f6ef2e889ee6fb`.

This is a **modified map-only integration**, not an original or official release
of Three Scope Map. It adapts classic `ZhejiangThreeMap.tsx` geometry, terrain
material, side gradient shader, chase ribbon and HUD arcs to native React 18
and Vietnamese data. It does not import the template's Earth, Chinese maps,
2D/overlay views, administrative drilldown or generated framework-neutral runtime.

The pinned author-owned code uses **Summer Platform Restriction License 1.1**
(`LicenseRef-Summer-Platform-Restriction-1.1`), not GPL. Keep source attribution
headers and the accompanying `licenses/LICENSE`, `NOTICE`, `CITATION.cff`,
`THIRD_PARTY_NOTICES.md` and applicable `LICENSES` records when distributing.
The original legal/provenance bundle is retained unmodified for reference; its
mentions of other template assets do not imply those assets are shipped here.
The archived GPL and 1.0 texts do not change the current code grant.

The current scope is a concrete heritage application, not a reusable paid map
platform. Consult the license before changing that product model; restricted
platform resale needs the author's written permission.

Geographic source attribution, transformation steps, exact hashes and CC0
terrain credits are in [`public/map/SOURCES.md`](../../public/map/SOURCES.md).

## Verification

From `apps/frontend`:

```sh
node --import tsx --test tests/heritage-map.test.ts
npx --no-install tsc --noEmit --incremental false
npm run dev
```

Browser acceptance: unframed mainland view without markers/inset/floating
controls, expandable list selection/close/Escape and detail links, gesture
rotation/zoom, desktop/mobile layout, keyboard selection, empty/API-error states,
asset retry/WebGL failure, resize, StrictMode remount and reduced motion. Use the actual API when available; browser
fixtures validate rendering/interaction but do not establish backend health.
