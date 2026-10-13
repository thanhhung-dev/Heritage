"use client";

import { useEffect, useRef, useState } from "react";
import { useHeritageTour } from "@/context/heritage-tour";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import type { ExploreMode } from "../three/explore-controller";
import type { TourEngine } from "../three/tour-engine";
import { useNarration } from "./useNarration";
import { useCaptions } from "./useCaptions";

export function useTourPlayer({ narrationUrl = null, captionsUrl = null }: {
  narrationUrl?: string | null;
  captionsUrl?: string | null;
} = {}) {
  const { engine, currentSceneKey, currentScene, scenePlayback } = useHeritageTour();
  const [isMuted, setIsMuted] = useState(false);
  const [ccOn, setCcOn] = useState(true);
  const [exploreMode, setExploreMode] = useState<ExploreMode | null>(null);
  const [selectedHighlight, setSelectedHighlight] = useState<HeritageInteractiveHighlight | null>(null);
  const [sceneError, setSceneError] = useState<string | null>(null);
  const [zoomed, setZoomed] = useState(false);
  const highlightEntry = useRef<ReturnType<TourEngine["getCameraPose"]> | null>(null);
  const timelineSceneKey = useRef<string | null>(null);
  const narration = useNarration(narrationUrl ?? scenePlayback?.narrationUrl ?? null, isMuted);
  const captions = useCaptions(captionsUrl ?? scenePlayback?.captionsUrl ?? null, narration.currentTime, ccOn);
  const { pause, seek } = narration;

  useEffect(() => {
    pause();
    seek(0);
    engine?.exitExplore();
    timelineSceneKey.current = null;
    engine?.setPlaybackTime(0, false);
    let cancelled = false;
    setSceneError(null);
    // Bay từ góc hiện tại tới góc mở đầu; chỉ instant_move mới đặt ngay.
    // Metadata audio đến sau sẽ bật timeline mà không hủy chuyến bay này.
    if (scenePlayback && currentScene) {
      engine?.stopCameraTimeline();
      engine?.flyCameraPreset(currentScene.camera, false, currentScene.camera.instant_move ? 0 : 1.6);
    } else {
      engine?.stopCameraTimeline();
    }
    engine?.setInteractiveHighlights(scenePlayback ? currentScene?.interactive.flatMap((i) => i.highlights) ?? [] : []);
    void engine?.setSceneHighlights(scenePlayback?.timedHighlights ?? []).catch((error: unknown) => {
      if (!cancelled) setSceneError(error instanceof Error ? error.message : "Không tải được highlight.");
    });
    setExploreMode(null);
    setSelectedHighlight(null);
    setZoomed(false);
    highlightEntry.current = null;
    const unsubscribe = engine?.onHighlightSelect((item) => {
      setSelectedHighlight(item);
      if (item && scenePlayback && currentScene && item.cam_pos && item.cam_target) {
        highlightEntry.current ??= engine.getCameraPose();
        engine.applyCameraPreset({ ...currentScene.camera, start_position: item.cam_pos, start_target: item.cam_target });
      }
      if (!item) highlightEntry.current = null;
    });
    return () => { cancelled = true; unsubscribe?.(); };
  }, [engine, currentSceneKey, currentScene, scenePlayback, pause, seek]);
  useEffect(() => {
    // Truyền cả trạng thái phát: engine cần biết để tự tiến đồng hồ nội bộ giữa
    // các lần React báo thời gian (mượt 60fps thay vì giật theo `timeupdate`).
    engine?.setPlaybackTime(narration.currentTime, narration.isPlaying);
  }, [engine, narration.currentTime, narration.isPlaying]);

  // Audio đọc xong metadata ⇒ biết thời lượng clip. Bật timeline đúng MỘT lần cho
  // mỗi cảnh: nếu bật lại mỗi khi `duration` đổi, `restore(start)` bên trong sẽ
  // kéo camera giật về đầu cảnh giữa lúc đang bay.
  const hasAudio = narration.hasAudio;
  useEffect(() => {
    if (!hasAudio || !currentScene || !scenePlayback) return;
    if (currentScene.camera.instant_move) return;
    // Chưa biết thời lượng thì chưa bật được; chờ lần cập nhật kế tiếp.
    if (!narration.duration) return;
    if (timelineSceneKey.current === currentSceneKey) return;
    if (engine?.startCameraTimeline(currentScene.camera, narration.duration)) {
      timelineSceneKey.current = currentSceneKey;
    }
  }, [engine, hasAudio, narration.duration, currentScene, scenePlayback, currentSceneKey]);

  function applyInteractiveCamera() {
    const interactive = scenePlayback ? currentScene?.interactive[0] : null;
    if (interactive?.cam_pos && interactive.cam_target && currentScene) {
      engine?.applyCameraPreset({ ...currentScene.camera, start_position: interactive.cam_pos, start_target: interactive.cam_target });
    }
  }

  return {
    ...narration,
    error: sceneError ?? narration.error,
    isMuted, setIsMuted, ccOn, setCcOn,
    captionText: captions.text,
    captionsError: captions.error,
    exploreMode, selectedHighlight, zoomed,
    hasSceneData: scenePlayback !== null,
    initialExploreMode: currentScene?.interactive[0]?.mode === "free" ? "free" as const : "standard" as const,
    toggleCameraView() {
      // Chuyển giữa góc Start và góc Zoom cũng bay mượt. Người dùng chủ động
      // chọn góc thì timeline dừng, tránh bị kéo về quỹ đạo tự động.
      engine?.stopCameraTimeline();
      if (currentScene && engine?.flyCameraPreset(currentScene.camera, !zoomed, 1.2)) setZoomed(!zoomed);
    },
    enterExplore(mode: ExploreMode) {
      pause();
      // Explore là để người dùng tự do xoay — timeline phải nhường quyền,
      // nếu không camera sẽ bị kéo về quỹ đạo mỗi frame.
      engine?.stopCameraTimeline();
      engine?.enterExplore(mode);
      if (exploreMode === null) applyInteractiveCamera();
      setExploreMode(mode);
    },
    resetExplore() { engine?.selectHighlight(null); engine?.resetExplore(); applyInteractiveCamera(); },
    exitExplore() {
      engine?.exitExplore();
      setExploreMode(null);
      // Trả quyền lại cho timeline khi rời Explore (bỏ qua cảnh instant_move và
      // cảnh chưa biết thời lượng clip). Đánh dấu cảnh đã bật để effect bên trên
      // không bật lại lần nữa và kéo camera giật về pose start.
      if (currentScene && !currentScene.camera.instant_move && narration.duration) {
        if (engine?.startCameraTimeline(currentScene.camera, narration.duration)) {
          timelineSceneKey.current = currentSceneKey;
        }
      }
    },
    closeHighlight() {
      const pose = highlightEntry.current;
      engine?.selectHighlight(null);
      if (pose) engine?.restoreCameraPose(pose);
    },
    restart() { void narration.replay(); },
    skipVoiceover: narration.skipToEnd,
    seekBy: (seconds: number) => seek(narration.currentTime + seconds),
  };
}
