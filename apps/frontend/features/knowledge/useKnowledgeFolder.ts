"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { isAborted, knowledgeApi } from "../../services/knowledge.service";
import { appendKnowledgePage, readKnowledgePage } from "./folder-state";
import { useKnowledge } from "./KnowledgeProvider";
import type { KnowledgePage } from "./types";

export function useKnowledgeFolder(requestedPrefix?: string) {
  const { root, revision, remember, takeRootSeed } = useKnowledge();
  const prefix = requestedPrefix ?? root;
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{ page: KnowledgePage | null; loading: boolean; error?: unknown; more: boolean }>({ page: null, loading: true, more: false });
  const generation = useRef(0);
  const activeMore = useRef<AbortController | null>(null);
  const moreLock = useRef(false);
  useEffect(() => {
    const id = ++generation.current;
    activeMore.current?.abort(); moreLock.current = false;
    const controller = new AbortController();
    const initial = revision === 0 && attempt === 0 ? takeRootSeed(prefix) : null;
    setState({ page: initial, loading: !initial, more: false });
    if (!initial) void readKnowledgePage(knowledgeApi, prefix, undefined, controller.signal).then(page => {
      if (id !== generation.current || controller.signal.aborted) return;
      remember(page); setState({ page, loading: false, more: false });
    }).catch(error => {
      if (!isAborted(error) && id === generation.current && !controller.signal.aborted) setState({ page: null, loading: false, more: false, error });
    });
    return () => { controller.abort(); activeMore.current?.abort(); };
  }, [prefix, revision, attempt, remember, takeRootSeed]);

  const loadMore = useCallback(async () => {
    if (moreLock.current || !state.page?.nextContinuationToken) return;
    moreLock.current = true;
    const id = generation.current, current = state.page;
    const controller = new AbortController(); activeMore.current = controller;
    setState(previous => ({ ...previous, error: undefined, more: true }));
    try {
      const next = await readKnowledgePage(knowledgeApi, prefix, current.nextContinuationToken!, controller.signal);
      if (id !== generation.current || controller.signal.aborted) return;
      const combined = appendKnowledgePage(current, next);
      remember(combined); setState({ page: combined, loading: false, more: false });
    } catch (error) {
      if (!isAborted(error) && id === generation.current && !controller.signal.aborted) setState(previous => ({ ...previous, error, more: false }));
    } finally { if (id === generation.current) moreLock.current = false; }
  }, [state.page, prefix, remember]);
  return { ...state, prefix, loadMore, refresh: () => setAttempt(n => n + 1) };
}
