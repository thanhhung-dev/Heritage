export type Coordinate = [number, number];
export type RegionId = "hue" | "da-nang";
export type Polygon = Coordinate[][];
export type BoundaryFeature = {
  type: "Feature";
  properties: { id: RegionId; name: string };
  geometry: { type: "MultiPolygon"; coordinates: Polygon[] };
};
export type BoundaryCollection = { type: "FeatureCollection"; features: BoundaryFeature[] };
export type MapLocation = { lat: number | null; lng: number | null; display_map?: boolean };
export type Located<T extends MapLocation = MapLocation> = T & {
  lat: number; lng: number; mapRegion: RegionId;
};
export const REGION_NAMES: Record<RegionId, string> = { hue: "Huế", "da-nang": "Đà Nẵng" };

export function parseBoundaries(value: unknown): BoundaryCollection {
  const data = value as BoundaryCollection | null;
  if (data?.type !== "FeatureCollection" || !Array.isArray(data.features) || data.features.length !== 2) {
    throw new Error("Dữ liệu ranh giới Huế–Đà Nẵng không hợp lệ.");
  }
  const ids = new Set<RegionId>();
  for (const feature of data.features) {
    if (feature.type !== "Feature" || !feature.properties ||
        !["hue", "da-nang"].includes(feature.properties.id) ||
        typeof feature.properties.name !== "string" ||
        feature.geometry?.type !== "MultiPolygon" ||
        !Array.isArray(feature.geometry.coordinates) || !feature.geometry.coordinates.length) {
      throw new Error("Không đọc được vùng địa lý.");
    }
    ids.add(feature.properties.id);
    for (const polygon of feature.geometry.coordinates) {
      if (!Array.isArray(polygon) || !polygon.length) throw new Error("Polygon rỗng.");
      for (const ring of polygon) {
        if (!Array.isArray(ring) || ring.length < 4 || ring.some((point) =>
          !Array.isArray(point) || point.length !== 2 || !Number.isFinite(point[0]) ||
          !Number.isFinite(point[1]) || Math.abs(point[0]) > 180 || Math.abs(point[1]) > 90)) {
          throw new Error("Tọa độ ranh giới không hợp lệ.");
        }
        const first = ring[0], last = ring[ring.length - 1];
        if (first[0] !== last[0] || first[1] !== last[1]) throw new Error("Đường biên chưa khép kín.");
      }
    }
  }
  if (ids.size !== 2) throw new Error("Thiếu vùng địa lý.");
  return data;
}

// 0 = outside, 1 = inside, 2 = on boundary. Include land and hole boundaries.
function inRing([x, y]: Coordinate, ring: Coordinate[]): number {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [ax, ay] = ring[j], [bx, by] = ring[i];
    const cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax);
    if (Math.abs(cross) < 1e-10 && x >= Math.min(ax, bx) - 1e-10 &&
        x <= Math.max(ax, bx) + 1e-10 && y >= Math.min(ay, by) - 1e-10 &&
        y <= Math.max(ay, by) + 1e-10) return 2;
    if ((ay > y) !== (by > y) && x < ((bx - ax) * (y - ay)) / (by - ay) + ax) inside = !inside;
  }
  return inside ? 1 : 0;
}

export function regionAt(data: BoundaryCollection, point: Coordinate): RegionId | null {
  if (!point.every(Number.isFinite)) return null;
  for (const feature of data.features) for (const polygon of feature.geometry.coordinates) {
    const outer = inRing(point, polygon[0]);
    if (!outer) continue;
    if (outer === 2) return feature.properties.id;
    let inHole = false;
    for (const hole of polygon.slice(1)) {
      const relation = inRing(point, hole);
      if (relation === 2) return feature.properties.id;
      if (relation === 1) { inHole = true; break; }
    }
    if (!inHole) return feature.properties.id;
  }
  return null;
}

export function visibleHeritages<T extends MapLocation>(items: T[], data: BoundaryCollection): Located<T>[] {
  return items.flatMap((item) => {
    if (item.display_map === false || typeof item.lat !== "number" || typeof item.lng !== "number" ||
        !Number.isFinite(item.lat) || !Number.isFinite(item.lng) || Math.abs(item.lat) > 90 || Math.abs(item.lng) > 180) return [];
    const mapRegion = regionAt(data, [item.lng, item.lat]);
    return mapRegion ? [{ ...item, lat: item.lat, lng: item.lng, mapRegion }] : [];
  });
}

export function splitMapPanels(data: BoundaryCollection) {
  // Presentation split across the empty sea between local islands and Hoang Sa,
  // NOT an administrative boundary. Every polygon and original coordinate survives.
  const panel = (offshore: boolean): BoundaryCollection => ({
    type: "FeatureCollection",
    features: data.features.flatMap((feature) => {
      const coordinates = feature.geometry.coordinates.filter((polygon) => (polygon[0][0][0] > 110) === offshore);
      return coordinates.length ? [{ ...feature, geometry: { ...feature.geometry, coordinates } }] : [];
    }),
  });
  return { mainland: panel(false), offshore: panel(true) };
}

// Shared by geometry and markers; longitude is corrected at the map's mid-latitude.
export function createProjection(data: BoundaryCollection) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const feature of data.features) for (const polygon of feature.geometry.coordinates) {
    for (const ring of polygon) for (const [x, y] of ring) {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    }
  }
  const longitudeScale = Math.cos(((minY + maxY) / 2) * Math.PI / 180);
  const scale = Math.min(804 / ((maxX - minX) * longitudeScale), 474 / (maxY - minY));
  return ([x, y]: Coordinate): Coordinate => [
    (x - (minX + maxX) / 2) * longitudeScale * scale,
    (y - (minY + maxY) / 2) * scale,
  ];
}
