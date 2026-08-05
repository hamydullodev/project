"use client";

import * as React from "react";

import { streamAnalyzeDocument } from "@/lib/api";
import type { AnalysisInfo, AnalysisStatus } from "@/lib/types";

interface AnalyzeState {
  status: AnalysisStatus;
  info: AnalysisInfo | null;
  answer: string;
  errorMessage: string | null;
  askedAt: number | null;
  firstTokenAt: number | null;
  doneAt: number | null;
}

const INITIAL_STATE: AnalyzeState = {
  status: "idle",
  info: null,
  answer: "",
  errorMessage: null,
  askedAt: null,
  firstTokenAt: null,
  doneAt: null,
};

/**
 * Drives one document through the streaming `/api/analyze-document`
 * endpoint — the document-analysis counterpart to `use-ask.ts`'s
 * `useAsk()`, same state machine and same abort-in-flight-request
 * reasoning (see that file's docstring), just without a `sources`/
 * `answerFound` shape since there's no corpus retrieval involved here.
 */
export function useAnalyze() {
  const [state, setState] = React.useState<AnalyzeState>(INITIAL_STATE);
  const abortRef = React.useRef<AbortController | null>(null);

  const analyze = React.useCallback((file: File) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({
      status: "loading",
      info: null,
      answer: "",
      errorMessage: null,
      askedAt: Date.now(),
      firstTokenAt: null,
      doneAt: null,
    });

    streamAnalyzeDocument(
      file,
      {
        onInfo: (info) => {
          setState((prev) => ({ ...prev, status: "streaming", info }));
        },
        onToken: (text) => {
          setState((prev) => ({
            ...prev,
            answer: prev.answer + text,
            firstTokenAt: prev.firstTokenAt ?? Date.now(),
          }));
        },
        onDone: () => {
          setState((prev) => ({ ...prev, status: "done", doneAt: Date.now() }));
        },
        onError: (message) => {
          setState((prev) => ({ ...prev, status: "error", errorMessage: message }));
        },
      },
      controller.signal,
    ).catch((error: unknown) => {
      if (controller.signal.aborted) return; // superseded by a newer analyze() call
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

  React.useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return { ...state, analyze, reset };
}
