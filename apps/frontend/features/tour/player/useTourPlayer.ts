"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useHeritageTour } from "@/context/heritage-tour";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import { parseExploreArea } from "../three/explore-area";
import type { ExploreMode } from "../three/explore-controller";
import type { TourEngine } from "../three/tour-engine";
import { useNarration } from "./useNarration";
import { useCaptions } from "./useCaptions";

export function useTourPlayer({ narrationUrl = null, captionsUrl = null, interactiveRoute = false }: {
  narrationUrl?: string | null;
  captionsUrl?: string | null;
  /**
   * URL đang là route điểm tương tác `/content/{slug}/{sceneKey}/int`.
   *
   * Truyền vào từ layout (nơi biết URL) thay vì gọi hook router ở đây: hook này
   * được test bằng `renderToStaticMarkup` không có App Router context, mà
   * `useRouter()` của `next/navigation` sẽ throw khi thiếu context đó.
   */
  interactiveRoute?: boolean;
} = {}) {
  const { engine, currentSceneKey, currentScene, scenePlayback } = useHeritageTour();
  const interactive = scenePlayback ? currentScene?.interactive[0] ?? null : null;
  const [isMuted, setIsMuted] = useState(false);
  const [ccOn, setCcOn] = useState(true);
  const [selectedHighlight, setSelectedHighlight] = useState<HeritageInteractiveHighlight | null>(null);
  const [sceneError, setSceneError] = useState<string | null>(null);
  const [zoomed, setZoomed] = useState(false);
  const highlightEntry = useRef<ReturnType<TourEngine["getCameraPose"]> | null>(null);
  const timelineSceneKey = useRef<string | null>(null);
  /**
   * Engine đã thực sự vào explore chưa. Cần cờ này vì `exploreMode` là giá trị
   * suy ra (có thể đổi vì lý do khác), còn `enterExplore` phải chạy ĐÚNG MỘT LẦN
   * cho mỗi lần vào — gọi lại sẽ chụp đè pose "camera cũ" mà nút Reset cần.
   */
  const exploreActive = useRef(false);
  /** Engine mà `exploreActive` đang nói tới — engine mới thì phải vào lại từ đầu. */
  const exploreEngine = useRef<TourEngine | null>(null);
  const narration = useNarration(narrationUrl ?? scenePlayback?.narrationUrl ?? null, isMuted);
  const captions = useCaptions(captionsUrl ?? scenePlayback?.captionsUrl ?? null, narration.currentTime, ccOn);
  const { pause, seek } = narration;

  /**
   * OBB giới hạn vùng đi bộ. Ưu tiên dữ liệu của chính điểm tương tác (backend trả
   * cột JSONB, bản fixture trả object đã tách), rồi mới tới bản sao trong
   * `playback` — hai nguồn này bằng nhau ở fixture hiện tại nhưng API có thể chỉ có
   * một trong hai.
   *
   * Khai báo TRƯỚC các effect: effect đổi cảnh liệt kê nó trong mảng phụ thuộc, mà
   * mảng đó được đọc ngay tại chỗ gọi `useEffect` nên không thể đứng sau.
   */
  const exploreArea = useMemo(
    () => parseExploreArea(interactive?.explore_area) ?? scenePlayback?.exploreArea ?? null,
    [interactive, scenePlayback],
  );

  useEffect(() => {
    pause();
    seek(0);
    // Trước khi đổi cảnh: chốt pose người dùng đang thấy (có thể đang dí gần một
    // badge) để cảnh mới bay tiếp từ đó, không nhảy về preset cũ.
    engine?.releaseHighlightDolly();
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
    engine?.setInteractiveHighlights(interactive?.highlights ?? []);
    // Biên đi bộ thuộc về CẢNH, không thuộc lần vào/ra chế độ — đặt ở đây để đổi
    // cảnh là biên đổi theo, kể cả khi đang ở sẵn trong chế độ đi bộ.
    engine?.setExploreArea(exploreArea);
    void engine?.setSceneHighlights(scenePlayback?.timedHighlights ?? []).catch((error: unknown) => {
      if (!cancelled) setSceneError(error instanceof Error ? error.message : "Không tải được highlight.");
    });
    // Đổi cảnh là thoát explore; cờ phải hạ theo để effect đồng bộ bên dưới vào
    // lại được nếu URL vẫn còn `/int` (đi thẳng vào route điểm của cảnh khác).
    exploreActive.current = false;
    setSelectedHighlight(null);
    setZoomed(false);
    highlightEntry.current = null;
    const unsubscribe = engine?.onHighlightSelect((item) => {
      setSelectedHighlight(item);
      if (item && scenePlayback && currentScene && item.cam_pos && item.cam_target) {
        highlightEntry.current ??= engine.getCameraPose();
        engine.flyCameraPreset({ ...currentScene.camera, start_position: item.cam_pos, start_target: item.cam_target }, false, 1.2);
      }
      if (!item) highlightEntry.current = null;
    });
    return () => { cancelled = true; unsubscribe?.(); };
  }, [engine, currentSceneKey, currentScene, scenePlayback, interactive, exploreArea, pause, seek]);
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

  const applyInteractiveCamera = useCallback((duration = 1.2) => {
    if (interactive?.cam_pos && interactive.cam_target && currentScene) {
      return engine?.flyCameraPreset({ ...currentScene.camera, start_position: interactive.cam_pos, start_target: interactive.cam_target }, false, duration);
    }
    return false;
  }, [interactive, currentScene, engine]);

  /**
   * Chế độ explore suy ra TRỰC TIẾP từ dữ liệu điểm tương tác.
   *
   * `free_explore` KHÔNG phải "orbit tự do" mà là đi bộ dưới đất có hàng rào; tên
   * gọi `walk` mới nói đúng việc nó làm. `free` mới là orbit không giới hạn góc.
   */
  const initialExploreMode: ExploreMode =
    interactive?.mode === "free_explore" ? "walk"
    : interactive?.mode === "free" ? "free"
    : "standard";

  /**
   * Chế độ explore suy ra TRỰC TIẾP từ URL, không giữ state riêng.
   *
   * Giữ thêm một biến state cho cùng một thông tin là mầm lệch trạng thái: bấm
   * Exit thì state tắt mà URL vẫn còn `/int`; F5 vào `/int` thì state rỗng dù URL
   * nói đang ở 3D mode. Ở đây URL là nguồn sự thật duy nhất, `exploreMode` chỉ là
   * hình chiếu của nó nên hai thứ không thể nói khác nhau.
   *
   * Không có `interactive` (cảnh chưa có dữ liệu điểm) thì coi như không vào được.
   */
  const exploreMode: ExploreMode | null =
    interactiveRoute && interactive ? initialExploreMode : null;

  /**
   * URL đổi thì engine phải được lệnh tường minh: `enter` chụp pose hiện tại để
   * nút Reset quay về, `exit` khôi phục pose đó. `exploreActive` bảo đảm mỗi lần
   * vào chỉ gọi `enter` một lần — gọi lại sẽ chụp đè "camera cũ".
   */
  useEffect(() => {
    if (!engine) return;

    // Engine mới (canvas dựng lại) không biết gì về lần vào explore trước đó.
    if (exploreEngine.current !== engine) {
      exploreEngine.current = engine;
      exploreActive.current = false;
    }

    if (!exploreMode) {
      if (!exploreActive.current) return;
      exploreActive.current = false;
      engine.exitExplore(1.2);
      timelineSceneKey.current = null;
      // Trả quyền lại cho timeline khi rời Explore (bỏ qua cảnh instant_move và
      // cảnh chưa biết thời lượng clip). Đánh dấu cảnh đã bật để effect bên trên
      // không bật lại lần nữa và kéo camera giật về pose start.
      if (currentScene && !currentScene.camera.instant_move && narration.duration) {
        if (engine.startCameraTimeline(currentScene.camera, narration.duration)) {
          timelineSceneKey.current = currentSceneKey;
        }
      }
      return;
    }

    if (exploreActive.current) return;
    exploreActive.current = true;
    pause();
    // Explore là để người dùng tự do xoay — timeline phải nhường quyền, nếu không
    // camera sẽ bị kéo về quỹ đạo mỗi frame.
    engine.stopCameraTimeline();
    // Metadata tải trễ không được giành camera từ thao tác chủ động này.
    timelineSceneKey.current = currentSceneKey;
    if (exploreMode === "walk") {
      // Độ cao mắt lấy từ `cam_pos[1]` của điểm tương tác, KHÔNG lấy từ camera
      // hiện tại: lúc này camera còn ở pose cuối cảnh, chưa hạ xuống điểm xuất
      // phát (chuyến bay chạy ngay sau đây mới đưa nó xuống). Không có `cam_pos`
      // thì lùi về tâm hộp đi bộ, rồi mới tới độ cao hiện tại.
      const camPos = interactive?.cam_pos;
      const eyeHeight = Array.isArray(camPos)
        ? camPos[1]
        : (camPos as Record<string, number> | null | undefined)?.y ?? exploreArea?.center[1];
      engine.enterExplore(exploreMode, eyeHeight);
      applyInteractiveCamera();
    } else {
      engine.enterExplore(exploreMode);
      applyInteractiveCamera();
    }
  }, [engine, exploreMode, exploreArea, pause, currentSceneKey, currentScene, narration.duration, applyInteractiveCamera]);

  return {
    ...narration,
    error: sceneError ?? narration.error,
    isMuted, setIsMuted, ccOn, setCcOn,
    captionText: captions.text,
    captionsError: captions.error,
    exploreMode, selectedHighlight, zoomed, interactive,
    hasSceneData: scenePlayback !== null,
    initialExploreMode,
    /** Tiêu đề + mô tả của chế độ explore, chỉ có nghĩa khi ĐANG ở trong chế độ. */
    exploreTitle: exploreMode ? scenePlayback?.exploreTitle ?? null : null,
    exploreDescription: exploreMode ? scenePlayback?.exploreDescription ?? null : null,
    /** OBB giới hạn vùng đi bộ của cảnh hiện tại (`null` = không giới hạn). */
    exploreArea,
    toggleCameraView() {
      // Chuyển giữa góc Start và góc Zoom cũng bay mượt. Người dùng chủ động
      // chọn góc thì timeline dừng, tránh bị kéo về quỹ đạo tự động.
      engine?.stopCameraTimeline();
      if (currentScene && engine?.flyCameraPreset(currentScene.camera, !zoomed, 1.2)) {
        timelineSceneKey.current = currentSceneKey;
        setZoomed(!zoomed);
      }
    },
    resetExplore() {
      engine?.selectHighlight(null);
      // Reset = về đúng điểm xuất phát của chế độ (với đi bộ là `cam_pos`). Bay
      // mượt như mọi chế độ khác: `updateWalk` tự nhường quyền trong lúc bay nên
      // khoá độ cao không cắt ngang đường bay.
      if (!applyInteractiveCamera()) engine?.resetExplore(1.2);
    },
    closeHighlight() {
      const pose = highlightEntry.current;
      engine?.selectHighlight(null);
      if (pose) engine?.restoreCameraPose(pose, 1.2);
    },
    selectHighlight(id: number) { engine?.selectHighlight(id); },
    /** Cần gạt ảo (mobile) — toạ độ đã chuẩn hoá `[-1, 1]`. */
    setWalkStick(x: number, y: number) { engine?.setWalkStick(x, y); },
    releaseWalkStick() { engine?.releaseWalkStick(); },
    restart() { void narration.replay(); },
    skipVoiceover: narration.skipToEnd,
    seekBy: (seconds: number) => seek(narration.currentTime + seconds),
  };
}
