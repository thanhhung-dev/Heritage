"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { NarrationStatus } from "@/features/chat/types";

const EMPTY_PLAYBACK = { isPlaying: false, currentTime: 0, duration: 0, hasEnded: false,
  narrationStatus: "not_started" as NarrationStatus, error: null as string | null };

/** Audio thật; không giả lập đồng hồ khi chưa có URL narration. */
export function useNarration(url: string | null, muted = false) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const skipped = useRef(false);
  const [state, setState] = useState({ ...EMPTY_PLAYBACK, url });
  useEffect(() => {
    setState({ ...EMPTY_PLAYBACK, url });
    skipped.current = false;
    if (!url) return;
    const audio = new Audio(url);
    audio.preload = "metadata";
    audioRef.current = audio;
    const sync = () => {
      let playedSeconds = 0;
      for (let index = 0; index < audio.played.length; index++) {
        playedSeconds += audio.played.end(index) - audio.played.start(index);
      }
      const completed = audio.ended && Number.isFinite(audio.duration) && audio.duration > 0
        && playedSeconds / audio.duration >= 0.98;
      setState((previous) => ({
        ...previous,
        isPlaying: !audio.paused && !audio.ended,
        hasEnded: audio.ended,
        currentTime: audio.currentTime,
        duration: Number.isFinite(audio.duration) ? audio.duration : 0,
        narrationStatus: skipped.current ? "skipped" : completed ? "completed"
          : playedSeconds > 0 ? "partial" : "not_started",
      }));
    };
    const fail = () => setState((previous) => ({ ...previous, isPlaying: false, error: "Không tải được narration." }));
    const events = ["loadedmetadata", "durationchange", "timeupdate", "play", "pause", "ended", "seeked"];
    events.forEach((event) => audio.addEventListener(event, sync));
    audio.addEventListener("error", fail);
    return () => {
      events.forEach((event) => audio.removeEventListener(event, sync));
      audio.removeEventListener("error", fail);
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      audioRef.current = null;
    };
  }, [url]);
  useEffect(() => {
    if (audioRef.current) audioRef.current.muted = muted;
  }, [muted, url]);

  const play = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;
    try {
      await audio.play();
      if (audioRef.current === audio) setState((previous) => ({ ...previous, error: null }));
    } catch (cause) {
      // Autoplay bị chặn (chưa có thao tác của người dùng) KHÔNG phải lỗi: tour tự
      // phát narration khi vào scene nên trình duyệt hay chặn. Giữ im lặng và để
      // nút play của người dùng khởi động lại, thay vì hiện thông báo tiếng Anh
      // của Chrome ("play() failed because the user didn't interact…").
      const blocked = cause instanceof DOMException && cause.name === "NotAllowedError";
      if (audioRef.current === audio) setState((previous) => ({
        ...previous, isPlaying: false,
        error: blocked
          ? null
          : cause instanceof Error
            ? cause.message
            : "Không phát được narration.",
      }));
    }
  }, []);
  const pause = useCallback(() => audioRef.current?.pause(), []);
  const seek = useCallback((seconds: number) => {
    const audio = audioRef.current;
    if (audio && Number.isFinite(audio.duration)) audio.currentTime = Math.max(0, Math.min(audio.duration, seconds));
  }, []);
  // Tua về đầu rồi phát lại. Khác với seek khi duration chưa sẵn sàng:
  // đặt currentTime trực tiếp vẫn được, nên Replay chạy đúng cả trước lần phát đầu.
  const replay = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;
    skipped.current = false;
    audio.currentTime = 0;
    await play();
  }, [play]);
  // Nhảy tới cuối narration để kết thúc scene hiện tại (không chuyển scene).
  // Đặt currentTime = duration kích hoạt sự kiện "ended" và cập nhật UI.
  const skipToEnd = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !Number.isFinite(audio.duration)) return;
    skipped.current = true;
    audio.currentTime = audio.duration;
    audio.pause();
    setState((previous) => ({ ...previous, narrationStatus: "skipped" }));
  }, []);
  // Render đầu khi URL đổi vẫn giữ state cũ trước khi effect reset chạy.
  // Không để camera cảnh mới dùng nhầm duration/currentTime của audio cũ.
  const playback = state.url === url ? state : EMPTY_PLAYBACK;
  return { ...playback, narrationStatus: url ? playback.narrationStatus : "unavailable" as NarrationStatus,
    hasAudio: !!url, play, pause, seek, replay, skipToEnd };
}
