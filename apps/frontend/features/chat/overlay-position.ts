export interface OverlayPoint {
  x: number;
  y: number;
}

export interface OverlaySize {
  width: number;
  height: number;
}

export interface OverlayBounds {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/** Keep the handle reachable even when a viewport becomes smaller than the box. */
export function clampOverlayPosition(point: OverlayPoint, size: OverlaySize, bounds: OverlayBounds): OverlayPoint {
  return {
    x: Math.max(bounds.left, Math.min(point.x, bounds.right - size.width)),
    y: Math.max(bounds.top, Math.min(point.y, bounds.bottom - size.height)),
  };
}

export function overlayBesideAnchor(anchor: OverlayBounds, size: OverlaySize, bounds: OverlayBounds): OverlayPoint {
  return clampOverlayPosition({ x: anchor.right - size.width, y: anchor.bottom - size.height }, size, bounds);
}
