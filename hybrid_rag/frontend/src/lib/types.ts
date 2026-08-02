/**
 * Shapes mirroring the FastAPI backend's public contract
 * (`api/schemas.py`'s `SourceOut`, `api/routers/ask.py`'s SSE event
 * payloads). Kept as a small, explicit set of types rather than
 * generated from the OpenAPI schema (`/openapi.json`) — reasonable for
 * this project's small, stable surface; codegen would be worth
 * revisiting if the API grows significantly.
 */

export interface Source {
  chunk_id: string;
  law_name: string | null;
  article_number: string | null;
  section: string | null;
  page_number: number | null;
  text: string;
  dense_score: number | null;
  sparse_score: number | null;
  /** Min-max normalized [0, 1] variants — unlike the raw scores above (sparse_score in particular is an unbounded BM25 score), these are safe to render as a percentage. See api/schemas.py's SourceOut docstring. */
  dense_score_normalized: number | null;
  sparse_score_normalized: number | null;
  combined_score: number;
  reranker_score: number;
}

export type AskStatus = "idle" | "loading" | "streaming" | "done" | "error";

/** `event: info` payload from `POST /api/analyze-document` (api/routers/analyze.py). */
export interface AnalysisInfo {
  file_name: string;
  char_count: number;
  warnings: string[];
}

export type AnalysisStatus = "idle" | "loading" | "streaming" | "done" | "error";
