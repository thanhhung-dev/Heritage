"use client";

import { useEffect, useState } from "react";

export function parseVtt(source: string) {
  const timestamp = (text: string) => {
    const match = /^(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})$/.exec(text);
    if (!match || +match[2] > 59 || +match[3] > 59) return NaN;
    return +(match[1] ?? 0) * 3600 + +match[2] * 60 + +match[3] + +match[4] / 1000;
  };
  const cues: { start: number; end: number; text: string }[] = [];
  for (const block of source.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n").split(/\n\s*\n/)) {
    if (/^(WEBVTT|NOTE|STYLE|REGION)(?:\s|$)/.test(block)) continue;
    const lines = block.split("\n");
    const index = lines.findIndex((line) => line.includes("-->"));
    const match = index >= 0 ? /^(\S+)\s+-->\s+(\S+)/.exec(lines[index]) : null;
    if (!match) continue;
    const start = timestamp(match[1]);
    const end = timestamp(match[2]);
    if (Number.isFinite(start) && Number.isFinite(end) && end > start) {
      cues.push({ start, end, text: lines.slice(index + 1).join("\n").replace(/<[^>]*>/g, "") });
    }
  }
  return cues;
}

/** Phụ đề plain text cơ bản, có cue chồng nhau; chưa áp dụng styling/region VTT. */
export function useCaptions(url: string | null, seconds: number, enabled = true) {
  const [cues, setCues] = useState<ReturnType<typeof parseVtt>>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setCues([]);
    setError(null);
    if (!url) return;
    const controller = new AbortController();
    void fetch(url, { signal: controller.signal }).then(async (response) => {
      if (!response.ok) throw new Error(`Không tải được phụ đề (HTTP ${response.status}).`);
      const text = await response.text();
      if (!controller.signal.aborted) setCues(parseVtt(text));
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Không tải được phụ đề.");
    });
    return () => controller.abort();
  }, [url]);
  return {
    text: enabled ? cues.filter((cue) => seconds >= cue.start && seconds < cue.end).map((cue) => cue.text).join("\n") : "",
    error,
  };
}
