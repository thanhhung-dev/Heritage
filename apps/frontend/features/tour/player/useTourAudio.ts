"use client";

import { useCallback, useEffect, useRef } from "react";
import { TOUR_SFX } from "./audio-config";

/** Ambience sống xuyên scene; narration Pause không dừng âm thanh môi trường. */
export function useTourAudio(ambientUrl: string | null, transitionUrl: string | null, muted: boolean) {
  const ambientRef = useRef<HTMLAudioElement | null>(null);
  const transitionRef = useRef<HTMLAudioElement | null>(null);
  const exploreRef = useRef<HTMLAudioElement | null>(null);
  const finishTransitionRef = useRef<(() => void) | null>(null);
  const transitionSource = transitionUrl || TOUR_SFX.transition.url;
  const mutedRef = useRef(muted);
  mutedRef.current = muted;

  const stopTransition = useCallback(() => {
    finishTransitionRef.current?.();
    transitionRef.current?.pause();
  }, []);

  const startAmbient = useCallback(() => {
    const audio = ambientRef.current;
    if (audio && audio.paused && !document.hidden) void audio.play().catch(() => {});
  }, []);

  useEffect(() => {
    if (!ambientUrl) return;
    const audio = new Audio(ambientUrl);
    audio.loop = true;
    audio.muted = mutedRef.current;
    ambientRef.current = audio;
    startAmbient();
    // Trình duyệt có thể chặn autoplay: thử lại ở thao tác tiếp theo của người xem.
    window.addEventListener("pointerdown", startAmbient);
    window.addEventListener("keydown", startAmbient);
    return () => {
      window.removeEventListener("pointerdown", startAmbient);
      window.removeEventListener("keydown", startAmbient);
      ambientRef.current = null;
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    };
  }, [ambientUrl, startAmbient]);

  useEffect(() => {
    const audio = new Audio(transitionSource);
    audio.volume = TOUR_SFX.transition.volume;
    audio.muted = mutedRef.current;
    transitionRef.current = audio;
    return () => {
      stopTransition();
      transitionRef.current = null;
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    };
  }, [transitionSource, stopTransition]);

  useEffect(() => {
    const audio = new Audio(TOUR_SFX.exploreReveal.url);
    audio.volume = TOUR_SFX.exploreReveal.volume;
    audio.muted = mutedRef.current;
    exploreRef.current = audio;
    return () => {
      exploreRef.current = null;
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    };
  }, []);

  useEffect(() => {
    if (ambientRef.current) ambientRef.current.muted = muted;
    if (transitionRef.current) transitionRef.current.muted = muted;
    if (exploreRef.current) exploreRef.current.muted = muted;
  }, [muted]);

  useEffect(() => {
    const visibility = () => {
      if (document.hidden) {
        ambientRef.current?.pause();
        stopTransition();
        exploreRef.current?.pause();
      } else startAmbient();
    };
    document.addEventListener("visibilitychange", visibility);
    return () => document.removeEventListener("visibilitychange", visibility);
  }, [startAmbient, stopTransition]);

  const stopExploreReveal = useCallback(() => {
    const audio = exploreRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
  }, []);

  const playTransition = useCallback(() => {
    stopTransition();
    const audio = transitionRef.current;
    if (!audio || document.hidden) return Promise.resolve();
    stopExploreReveal();
    audio.currentTime = 0;
    return new Promise<void>((resolve) => {
      let finished = false;
      const finish = () => {
        if (finished) return;
        finished = true;
        window.clearTimeout(timer);
        ["ended", "error", "abort"].forEach((event) => audio.removeEventListener(event, finish));
        finishTransitionRef.current = null;
        audio.pause();
        resolve();
      };
      // Không để narration bị treo nếu request SFX bị kẹt mà không báo lỗi.
      const timer = window.setTimeout(finish, 10000);
      finishTransitionRef.current = finish;
      ["ended", "error", "abort"].forEach((event) => audio.addEventListener(event, finish));
      void audio.play().catch(finish);
    });
  }, [stopExploreReveal, stopTransition]);

  const playExploreReveal = useCallback(() => {
    const audio = exploreRef.current;
    if (!audio || document.hidden) return;
    // Hai SFX dùng chung không phát chồng; ambience không bị gián đoạn.
    stopTransition();
    audio.pause();
    audio.currentTime = 0;
    void audio.play().catch(() => {});
  }, [stopTransition]);

  return { playTransition, stopTransition, playExploreReveal, stopExploreReveal };
}
