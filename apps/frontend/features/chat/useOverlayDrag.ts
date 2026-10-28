"use client";

import { useCallback, useLayoutEffect, useRef, useState, type CSSProperties, type HTMLAttributes, type RefObject } from "react";
import { clampOverlayPosition, type OverlayBounds, type OverlayPoint } from "@/features/chat/overlay-position";

const dragThreshold = 6;
const interactive = "button, a, input, textarea, select, [contenteditable='true']";
type DragHandlers = Pick<HTMLAttributes<HTMLElement>, "onPointerDown" | "onPointerMove" | "onPointerUp"
  | "onPointerCancel" | "onLostPointerCapture" | "onClickCapture" | "onKeyDown">;

interface DragSession {
  pointerId: number;
  handle: HTMLElement;
  start: OverlayPoint;
  origin: OverlayPoint;
  moved: boolean;
}

function viewportBounds(element: HTMLElement): OverlayBounds {
  const viewport = window.visualViewport;
  const styles = window.getComputedStyle(element);
  const inset = (side: string) => Math.max(12, Number.parseFloat(styles.getPropertyValue(`--chat-safe-${side}`)) || 0);
  return {
    left: (viewport?.offsetLeft ?? 0) + inset("left"),
    top: (viewport?.offsetTop ?? 0) + inset("top"),
    right: (viewport?.offsetLeft ?? 0) + (viewport?.width ?? window.innerWidth) - inset("right"),
    bottom: (viewport?.offsetTop ?? 0) + (viewport?.height ?? window.innerHeight) - inset("bottom"),
  };
}

export function useOverlayDrag(
  target: RefObject<HTMLElement>,
  { enabled = true, ignoreInteractive = false, layoutKey = "" } = {},
) {
  const [position, setPosition] = useState<OverlayPoint | null>(null);
  const [dragging, setDragging] = useState(false);
  const [viewport, setViewport] = useState<{ width: number; height: number } | null>(null);
  const current = useRef<OverlayPoint | null>(null);
  const session = useRef<DragSession | null>(null);
  const suppressClick = useRef(false);

  const place = useCallback((point: OverlayPoint) => {
    const element = target.current;
    if (!element) return;
    const next = clampOverlayPosition(point, { width: element.offsetWidth, height: element.offsetHeight }, viewportBounds(element));
    current.current = next;
    setPosition((previous) => previous?.x === next.x && previous.y === next.y ? previous : next);
  }, [target]);

  const release = useCallback(() => {
    const active = session.current;
    session.current = null;
    if (active?.handle.hasPointerCapture(active.pointerId)) active.handle.releasePointerCapture(active.pointerId);
  }, []);

  useLayoutEffect(() => {
    const element = target.current;
    if (!element) return;
    const synchronize = () => {
      const visual = window.visualViewport;
      const width = visual?.width ?? window.innerWidth;
      const height = visual?.height ?? window.innerHeight;
      setViewport((previous) => previous?.width === width && previous.height === height ? previous : { width, height });
      if (current.current) place(current.current);
    };
    const resize = () => { release(); setDragging(false); synchronize(); };
    synchronize();
    const observer = new ResizeObserver(synchronize);
    observer.observe(element);
    window.addEventListener("resize", resize);
    window.visualViewport?.addEventListener("resize", resize);
    window.visualViewport?.addEventListener("scroll", resize);
    return () => {
      release();
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.visualViewport?.removeEventListener("resize", resize);
      window.visualViewport?.removeEventListener("scroll", resize);
    };
  }, [target, place, release]);

  useLayoutEffect(() => {
    if (!enabled) { release(); setDragging(false); return; }
    if (current.current) place(current.current);
  }, [enabled, layoutKey, place, release]);

  const handlers: DragHandlers = {
    onPointerDown(event) {
      if (!enabled || !event.isPrimary || event.button !== 0 || session.current) return;
      if (ignoreInteractive && event.target instanceof Element && event.target.closest(interactive)) return;
      const element = target.current;
      if (!element) return;
      event.stopPropagation();
      suppressClick.current = false;
      const rect = element.getBoundingClientRect();
      session.current = {
        pointerId: event.pointerId, handle: event.currentTarget, moved: false,
        start: { x: event.clientX, y: event.clientY }, origin: { x: rect.left, y: rect.top },
      };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    onPointerMove(event) {
      const active = session.current;
      if (!active || active.pointerId !== event.pointerId) return;
      event.stopPropagation();
      const dx = event.clientX - active.start.x;
      const dy = event.clientY - active.start.y;
      if (!active.moved && Math.hypot(dx, dy) < dragThreshold) return;
      event.preventDefault();
      active.moved = true;
      suppressClick.current = true;
      setDragging(true);
      place({ x: active.origin.x + dx, y: active.origin.y + dy });
    },
    onPointerUp(event) {
      const active = session.current;
      if (!active || active.pointerId !== event.pointerId) return;
      event.stopPropagation();
      if (active.moved) place({ x: active.origin.x + event.clientX - active.start.x, y: active.origin.y + event.clientY - active.start.y });
      release();
      setDragging(false);
    },
    onPointerCancel(event) {
      if (session.current?.pointerId !== event.pointerId) return;
      event.stopPropagation();
      release();
      setDragging(false);
    },
    onLostPointerCapture(event) {
      if (session.current?.pointerId !== event.pointerId) return;
      session.current = null;
      setDragging(false);
    },
    onClickCapture(event) {
      if (suppressClick.current && event.detail !== 0) {
        event.preventDefault();
        event.stopPropagation();
        suppressClick.current = false;
      }
    },
    onKeyDown(event) {
      if (!enabled || event.target !== event.currentTarget || event.altKey || event.ctrlKey || event.metaKey) return;
      const directions: Record<string, OverlayPoint> = {
        ArrowLeft: { x: -1, y: 0 }, ArrowRight: { x: 1, y: 0 }, ArrowUp: { x: 0, y: -1 }, ArrowDown: { x: 0, y: 1 },
      };
      const direction = directions[event.key];
      if (!direction || !target.current) return;
      event.preventDefault();
      event.stopPropagation();
      const rect = target.current.getBoundingClientRect();
      const step = event.shiftKey ? 40 : 10;
      place({ x: rect.left + direction.x * step, y: rect.top + direction.y * step });
    },
  };
  const style = {
    ...(viewport ? { "--chat-viewport-width": `${viewport.width}px`, "--chat-viewport-height": `${viewport.height}px` } : {}),
    ...(position ? { left: position.x, top: position.y } : {}),
  } as CSSProperties;
  return { position, dragging, style, handlers, place };
}
