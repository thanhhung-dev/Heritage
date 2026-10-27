"use client";

import { useCallback, useEffect, useState } from "react";
import { searchHeritages } from "@/services/heritageSearchService";
import type { SearchResults, SearchState } from "./types";

type SearchSnapshot =
  | { key: string; status: "loading" }
  | { key: string; status: "error" }
  | { key: string; status: "success"; results: SearchResults };

export function useHeritageSearch(state: SearchState) {
  const { q, region, category, page } = state;
  const key = JSON.stringify([q, region, category, page]);
  const [attempt, setAttempt] = useState(0);
  const [snapshot, setSnapshot] = useState<SearchSnapshot>({ key, status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    setSnapshot({ key, status: "loading" });
    searchHeritages({ q, region, category, page }, controller.signal)
      .then((results) => {
        if (active) setSnapshot({ key, status: "success", results });
      })
      .catch(() => {
        if (active) setSnapshot({ key, status: "error" });
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [q, region, category, page, key, attempt]);

  const retry = useCallback(() => setAttempt((current) => current + 1), []);
  return {
    snapshot: snapshot.key === key ? snapshot : { key, status: "loading" } as SearchSnapshot,
    retry,
  };
}
