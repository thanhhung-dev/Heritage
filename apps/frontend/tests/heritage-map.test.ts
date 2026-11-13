import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  parseBoundaries, parseDistricts, regionAt, districtAt, visibleHeritages,
  splitMapPanels, filterMainlandDistricts, createProjection, createInverseProjection,
  type BoundaryCollection,
} from "../features/map/geography";

const boundaryPath = new URL("../public/map/hue-da-nang.geojson", import.meta.url);
const districtPath = new URL("../public/map/hue-da-nang-districts.geojson", import.meta.url);
const boundaries = () => parseBoundaries(JSON.parse(readFileSync(boundaryPath, "utf8")));
const districts = () => parseDistricts(JSON.parse(readFileSync(districtPath, "utf8")));

test("map uses the post-merger Hue and Da Nang boundaries, including Quang Nam and islands", () => {
  const data = boundaries();
  assert.deepEqual(data.features.map((f) => f.properties.id).sort(), ["da-nang", "hue"]);
  assert.equal(regionAt(data, [107.579, 16.469]), "hue");
  assert.equal(regionAt(data, [108.202, 16.054]), "da-nang");
  assert.equal(regionAt(data, [108.328, 15.88]), "da-nang", "Hoi An, former Quang Nam");
  assert.equal(regionAt(data, [108.47, 15.57]), "da-nang", "Tam Ky, former Quang Nam");
  assert.equal(regionAt(data, [105.85, 21.03]), null, "Ha Noi must not appear");
  assert.equal(regionAt(data, [16.469, 107.579]), null, "lat/lng must not be swapped");
  const { mainland, offshore } = splitMapPanels(data);
  const count = (collection: BoundaryCollection) => collection.features.reduce((n, f) => n + f.geometry.coordinates.length, 0);
  assert.equal(count(mainland) + count(offshore), 34, "no polygon is discarded");
  assert.ok(count(offshore) > 0);
  for (const feature of offshore.features) {
    for (const polygon of feature.geometry.coordinates) {
      assert.equal(regionAt(data, polygon[0][0]), "da-nang", "offshore boundary stays in Da Nang");
    }
  }
});

test("region lookup handles boundary points, holes and disconnected polygons", () => {
  const data: BoundaryCollection = { type: "FeatureCollection", features: [{
    type: "Feature", properties: { id: "hue", name: "Huế" },
    geometry: { type: "MultiPolygon", coordinates: [
      [[[0, 0], [8, 0], [8, 6], [0, 6], [0, 0]], [[2, 2], [4, 2], [4, 4], [2, 4], [2, 2]]],
      [[[10, 1], [12, 1], [12, 3], [10, 3], [10, 1]]],
    ] },
  }] };
  assert.equal(regionAt(data, [1, 3]), "hue");
  assert.equal(regionAt(data, [3, 3]), null, "inside a hole is not land");
  assert.equal(regionAt(data, [2, 3]), "hue", "boundary is included");
  assert.equal(regionAt(data, [8, 4]), "hue", "outer boundary is included");
  assert.equal(regionAt(data, [11, 2]), "hue");
  assert.equal(regionAt(data, [9, 2]), null);
  assert.equal(regionAt(data, [NaN, 3]), null);
});

test("only valid, visible heritages inside the two regions are mapped, regardless of old region labels", () => {
  const items = [
    { slug: "hoi-an", lat: 15.88, lng: 108.328, region: "Quảng Nam", display_map: true },
    { slug: "hidden", lat: 16.469, lng: 107.579, display_map: false },
    { slug: "hanoi", lat: 21.03, lng: 105.85, display_map: true },
    { slug: "missing", lat: null, lng: 108.2, display_map: true },
    { slug: "invalid", lat: Infinity, lng: 108.2, display_map: true },
  ];
  const result = visibleHeritages(items, boundaries());
  assert.deepEqual(result.map((p) => [p.slug, p.mapRegion]), [["hoi-an", "da-nang"]]);
});

test("both panels project north up and east right without mutating source coordinates", () => {
  const data = boundaries();
  const original = JSON.stringify(data);
  for (const panel of Object.values(splitMapPanels(data))) {
    const project = createProjection(panel);
    const west = project([107.2, 16]);
    const east = project([108.2, 16]);
    const north = project([107.2, 17]);
    assert.ok(east[0] > west[0]);
    assert.ok(north[1] > west[1]);
    assert.equal(east[1], west[1]);
    assert.equal(north[0], west[0]);
    for (const feature of panel.features) for (const polygon of feature.geometry.coordinates) {
      for (const ring of polygon) for (const coord of ring) {
        const [x, y] = project(coord);
        assert.ok(Math.abs(x) <= 402.001 && Math.abs(y) <= 237.001);
      }
    }
  }
  assert.equal(JSON.stringify(data), original);
});

test("malformed boundary data is rejected instead of rendering misleading geometry", () => {
  for (const value of [null, {}, { type: "FeatureCollection", features: [] }]) {
    assert.throws(() => parseBoundaries(value));
    assert.throws(() => parseDistricts(value));
  }
});

test("post-merger wards/communes load, filter mainland, and invert projection accurately", () => {
  const data = districts();
  const hueCount = data.features.filter((f) => f.properties.region === "hue").length;
  const dnCount = data.features.filter((f) => f.properties.region === "da-nang").length;
  assert.equal(hueCount, 40);
  assert.equal(dnCount, 94);

  const mainlandDistricts = filterMainlandDistricts(data);
  assert.ok(mainlandDistricts.features.length < data.features.length, "Hoang Sa offshore unit is excluded from mainland");

  const { mainland } = splitMapPanels(boundaries());
  const project = createProjection(mainland);
  const unproject = createInverseProjection(mainland);
  const sample: [number, number] = [108.202, 16.054];
  const [lng, lat] = unproject(project(sample));
  assert.ok(Math.abs(lng - sample[0]) < 1e-9 && Math.abs(lat - sample[1]) < 1e-9);

  const hit = districtAt(mainlandDistricts, sample);
  assert.ok(hit !== null && hit.properties.region === "da-nang");
});
