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
  combined_score: number;
  reranker_score: number;
}

export type AskStatus = "idle" | "loading" | "streaming" | "done" | "error";
