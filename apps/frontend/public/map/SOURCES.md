# Huế–Đà Nẵng map assets

## Administrative boundaries

Source: General Statistics Office of Vietnam (GSO), contributed by OCHA ROAP,
quality assured and published by OCHA / Humanitarian Data Exchange (HDX).

- Dataset: https://data.humdata.org/dataset/cod-ab-vnm
- Version: COD-AB v02, 34 administrative level-1 units.
- Source boundaries created: 2025-07-01; reviewed: 2025-09-25.
- Downloaded: 2026-11-13.
- Resource: https://data.humdata.org/dataset/3cb544a9-9d04-4f54-94e2-93230efd8ceb/resource/048a6012-a8c2-4fa9-be87-cb6c01e9afbf/download/vnm_admin_boundaries.geojson.zip
- License: Creative Commons Attribution 3.0 IGO (CC BY-IGO).
  https://creativecommons.org/licenses/by/3.0/igo/legalcode
- Source ZIP SHA-256: `0a74e8ee18eb84b21f980fa4bd2a3135d2bc42fbd6e31450472368ff48abe41b`.
- Derived `hue-da-nang.geojson` SHA-256: `b17c7ac468265a017d699fc3c9f3c829df05af5a115cc7d06840a724e05b2963`.

HeritageGraph modifications: select `VN46` (Huế) and `VN48` (Đà Nẵng) from
`vnm_admin1.geojson`, replace properties with application IDs and Vietnamese
names, serialize as a minified FeatureCollection. Geometry is unchanged:
34 polygons, 54,134 coordinate positions, including holes and offshore islands.
Source CRS is OGC CRS84 (longitude, latitude; WGS84).

The current presentation shows the mainland and nearby islands, without a
Hoàng Sa inset. Polygons east of 110°E are excluded from rendering only, not
removed from the source GeoJSON. This meridian lies in the empty sea gap between
the two groups; it is not an administrative or maritime boundary. No source
polygon or coordinate is removed, translated, or simplified.
Data is a visualization source, not a legal survey or navigation chart. No
endorsement by GSO, OCHA or HDX is implied.

## Decorative terrain textures

`textures/terrain-{diffuse,height,normal,roughness}.jpg` are the classic Three
Scope Map template's **Rocky Terrain** 1K assets by **Amal Kumar / Poly Haven**.
License: CC0-1.0, https://polyhaven.com/license
Asset: https://polyhaven.com/a/rocky_terrain

Exact source URLs and SHA-256 records are retained in
`features/map/licenses/LICENSES/asset-sources.json` (relative to the frontend
source root). All four bundled files were verified against those hashes.
These repeated material textures are decorative and do not represent measured
elevation or imagery of Huế, Đà Nẵng or Hoàng Sa.

## Renderer attribution

Based on three-scope-map-skill by 宋夏天Dazzle.
作者全平台ID：宋夏天Dazzle；公众号：送你整个夏天
Original repository: https://github.com/songsummer920-dazzle/three-scope-map-skill
Revision: `f8c93697c010801e203c9b9f49f6ef2e889ee6fb`.
Adapted for HeritageGraph; this is not an official upstream release.
Source and license details: `features/map/README.md` and `features/map/licenses/`.
