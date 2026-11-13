"use client";

// SPDX-License-Identifier: LicenseRef-Summer-Platform-Restriction-1.1
// Copyright (c) 2026 宋夏天Dazzle
// 作者全平台ID：宋夏天Dazzle；公众号：送你整个夏天
// Source: https://github.com/songsummer920-dazzle/three-scope-map-skill
// Modified for HeritageGraph: React 18 host for the adapted classic map-only scene.
import { useEffect, useImperativeHandle, useRef, type Ref } from "react";
import type { HeritageSummary } from "@/types/heritage";
import { createMapEngine, type MapEngine } from "./map-engine";
import type { BoundaryCollection, Located } from "./geography";
import styles from "./map.module.css";

export type MapHandle = Pick<MapEngine, "zoom" | "resetView" | "focus">;
type Props = {
  controlsRef: Ref<MapHandle>;
  data: BoundaryCollection;
  onBackgroundClick: () => void;
  locations: Located<HeritageSummary>[];
  selectedSlug: string | null;
  onSelect: (slug: string, trigger: HTMLButtonElement) => void;
  onReady: () => void;
  onError: (message: string) => void;
};

export default function HeritageMap(props: Props) {
  const host = useRef<HTMLDivElement>(null);
  const engine = useRef<MapEngine | null>(null);
  const markerElements = useRef(new Map<string, HTMLButtonElement>());
  const callbacks = useRef(props);
  callbacks.current = props;
  useImperativeHandle(props.controlsRef, () => ({
    zoom: (factor) => engine.current?.zoom(factor),
    resetView: () => engine.current?.resetView(),
    focus: (coordinate) => engine.current?.focus(coordinate),
  }), []);

  useEffect(() => {
    if (!host.current) return;
    try {
      const map = createMapEngine(host.current, props.data, {
        onReady: () => {
          callbacks.current.onReady();
          const selected = callbacks.current.locations.find((place) => place.slug === callbacks.current.selectedSlug);
          if (selected) engine.current?.focus([selected.lng, selected.lat]);
        },
        onError: (message) => callbacks.current.onError(message),
        onBackgroundClick: () => callbacks.current.onBackgroundClick(),
      });
      engine.current = map;
      return () => { map.dispose(); engine.current = null; };
    } catch {
      callbacks.current.onError("Không khởi tạo được WebGL. Kiểm tra hỗ trợ đồ họa của trình duyệt rồi thử lại.");
    }
  }, [props.data]);

  useEffect(() => {
    engine.current?.setMarkers(props.locations.flatMap((place) => {
      const element = markerElements.current.get(place.slug);
      return element ? [{ coordinate: [place.lng, place.lat], element }] : [];
    }));
  }, [props.data, props.locations]);

  return (
    <div className={styles.host} ref={host}>
      <div className={styles.markers}>
        {props.locations.map((place) => (
          <button
            key={place.slug}
            ref={(element) => {
              if (element) markerElements.current.set(place.slug, element);
              else markerElements.current.delete(place.slug);
            }}
            className={styles.marker}
            type="button"
            data-heritage-marker={place.slug}
            aria-label={`Xem thông tin ${place.title}`}
            aria-pressed={props.selectedSlug === place.slug}
            aria-controls={props.selectedSlug === place.slug ? "heritage-selected-card" : undefined}
            onClick={(event) => props.onSelect(place.slug, event.currentTarget)}
          >
            <span className={styles.markerPulse} aria-hidden="true" />
            <span className={styles.markerCore} aria-hidden="true" />
            <span className={styles.markerName} aria-hidden="true">{place.title}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
