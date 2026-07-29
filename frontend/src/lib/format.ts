/**
 * Small display-formatting helpers for the result card's metadata row.
 * None of these need a backend change — `reranker_score` is already a
 * sigmoid-mapped [0, 1] relevance probability (see
 * `app/reranker/cross_encoder.py`'s docstring), and reading time/response
 * time are natural client-side computations from the answer text and the
 * SSE event timestamps `useAsk` already captures.
 */

const WORDS_PER_MINUTE = 200;

/** Whole minutes to read `text` aloud... well, silently, at ~200 wpm. Never rounds down to 0. */
export function readingTimeMinutes(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}

export type ConfidenceLevel = "high" | "medium" | "low";

export interface ConfidenceInfo {
  level: ConfidenceLevel;
  label: string;
}

/**
 * Buckets the top source's `reranker_score` into a coarse, honest label
 * rather than surfacing the raw probability as a fake-precise percentage
 * — a cross-encoder's sigmoid output is a relevance signal, not a
 * calibrated "this answer is correct" confidence, so a bucketed label
 * makes a claim the number can actually support.
 */
export function confidenceInfo(topRerankerScore: number | undefined): ConfidenceInfo {
  const score = topRerankerScore ?? 0;
  if (score >= 0.75) return { level: "high", label: "Yuqori ishonch" };
  if (score >= 0.5) return { level: "medium", label: "Oʻrtacha ishonch" };
  return { level: "low", label: "Past ishonch" };
}

/** `1284` -> "1.3s", `840` -> "0.8s" — always one decimal, always seconds (answers here take low single-digit seconds, never long enough to need minutes). */
export function formatDuration(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}
