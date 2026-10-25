"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { readSearchState, searchHref, updateSearchParams } from "./search-params";
import type { SearchState } from "./types";

export function useSearchUrl() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const serialized = searchParams.toString();
  const state = useMemo(() => readSearchState(new URLSearchParams(serialized)), [serialized]);
  const [draft, setDraft] = useState(state.q);
  const [composing, setComposing] = useState(false);
  const [pending, startTransition] = useTransition();
  const paramsRef = useRef(serialized);
  const committedRef = useRef(serialized);
  const submittedQuery = useRef<string | null>(null);

  // Keep rapid filter changes together even before an App Router navigation commits.
  if (committedRef.current !== serialized) {
    committedRef.current = serialized;
    paramsRef.current = serialized;
  }

  const navigate = useCallback((patch: Partial<SearchState>, replace = false) => {
    const next = updateSearchParams(new URLSearchParams(paramsRef.current), patch);
    if (next.toString() === paramsRef.current) return;
    paramsRef.current = next.toString();
    submittedQuery.current = readSearchState(next).q;
    startTransition(() => {
      const href = searchHref(next);
      if (replace) router.replace(href, { scroll: false });
      else router.push(href, { scroll: false });
    });
  }, [router]);

  useEffect(() => {
    // Back/Forward replaces the draft; our own debounced navigation preserves newer typing.
    if (submittedQuery.current !== state.q) setDraft(state.q);
    submittedQuery.current = null;
  }, [serialized, state.q]);

  useEffect(() => {
    if (composing || draft.trim() === state.q) return;
    const timer = window.setTimeout(() => navigate({ q: draft, page: 1 }, true), 400);
    return () => window.clearTimeout(timer);
  }, [draft, composing, state.q, serialized, navigate]);

  return {
    state, draft, setDraft, setComposing, navigate,
    busy: pending || composing || draft.trim() !== state.q,
    submit: () => { if (!composing) navigate({ q: draft, page: 1 }); },
    filter: (patch: Pick<Partial<SearchState>, "region" | "category">) => navigate({ ...patch, q: draft, page: 1 }),
    reset: () => {
      setDraft("");
      navigate({ q: "", region: "", category: "", page: 1 });
    },
    hrefForPage: (page: number) => searchHref(new URLSearchParams(serialized), { page }),
  };
}
