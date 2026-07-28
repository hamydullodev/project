"use client";

import * as React from "react";

import { streamAsk } from "@/lib/api";
import type { AskStatus, Source } from "@/lib/types";

interface AskState {
  status: AskStatus;
  query: string;
  sources: Source[];
  answer: string;
  answerFound: boolean;
  errorMessage: string | null;
}

const INITIAL_STATE: AskState = {
  status: "idle",
  query: "",
  sources: [],
  answer: "",
  answerFound: true,
  errorMessage: null,
};

/**
 * Drives one question through the streaming `/api/ask` endpoint and
 * exposes its progress as plain React state.
 *
 * WHY `ask()` ABORTS ANY IN-FLIGHT REQUEST BEFORE STARTING A NEW ONE
 * ------------------------------------------------------------------------
 * A user can submit a new question (typing + Enter, or clicking a
 * suggestion chip) while a previous answer is still streaming — without
 * cancellation, both requests' `onToken` callbacks would interleave
 * into the same `answer` string, corrupting it. `AbortController` lets
 * the previous `fetch()` be torn down cleanly; its callbacks are guarded
 * against firing after abort in `streamAsk`'s caller below.
 */
export function useAsk() {
  const [state, setState] = React.useState<AskState>(INITIAL_STATE);
  const abortRef = React.useRef<AbortController | null>(null);

  const ask = React.useCallback((rawQuery: string) => {
    const query = rawQuery.trim();
    if (!query) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({
      status: "loading",
      query,
      sources: [],
      answer: "",
      answerFound: true,
      errorMessage: null,
    });

    streamAsk(
      query,
      {
        onSources: (_query, sources) => {
          setState((prev) => ({ ...prev, status: "streaming", sources }));
        },
        onToken: (text) => {
          setState((prev) => ({ ...prev, answer: prev.answer + text }));
        },
        onDone: (answerFound) => {
          setState((prev) => ({ ...prev, status: "done", answerFound }));
        },
        onError: (message) => {
          setState((prev) => ({ ...prev, status: "error", errorMessage: message }));
        },
      },
      controller.signal,
    ).catch((error: unknown) => {
      if (controller.signal.aborted) return; // superseded by a newer ask() call
      setState((prev) => ({
        ...prev,
        status: "error",
        errorMessage: error instanceof Error ? error.message : "Nomaʼlum xatolik yuz berdi.",
      }));
    });
  }, []);

  const reset = React.useCallback(() => {
    abortRef.current?.abort();
    setState(INITIAL_STATE);
  }, []);

  // Abort any in-flight request if the component using this hook unmounts.
  React.useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return { ...state, ask, reset };
}
