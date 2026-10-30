"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchHeritageCatalogue, selectHeritages } from "@/services/heritageSearchService";
import type { HeritageSearchItem, SearchState } from "./types";

type CatalogueSnapshot = { status: "loading" } | { status: "error" } | { status: "success"; items: HeritageSearchItem[] };

export function useHeritageSearch(state: SearchState) {
  const [attempt, setAttempt] = useState(0);
  const [catalogue, setCatalogue] = useState<CatalogueSnapshot>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    setCatalogue({ status: "loading" });
    fetchHeritageCatalogue(controller.signal)
      .then((items) => { if (active) setCatalogue({ status: "success", items }); })
      .catch(() => { if (active) setCatalogue({ status: "error" }); })
      .finally(() => window.clearTimeout(timeout));
    return () => { active = false; controller.abort(); window.clearTimeout(timeout); };
  }, [attempt]);
  const results = useMemo(() => catalogue.status === "success" ? selectHeritages(catalogue.items, state) : null, [catalogue, state]);
  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  return { status: catalogue.status, results, retry };
}
