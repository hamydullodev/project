# Changelog

This project doesn't cut versioned releases (it's a local-first,
single-branch project) — this log tracks major phases of work instead.
See `git log` for the full, granular commit history.

## [Unreleased] — 2026-07-29 — Premium redesign & GitHub presentation

- Rebranded to **UzLaw AI** with a new scale-of-justice + Uzbekistan
  flag SVG mark.
- Dark-default theme, ambient motion, Framer Motion hero/search
  transitions, a staged retrieval indicator.
- Result card: Markdown rendering, reading time / confidence / response
  time metadata, Copy / Markdown-toggle / PDF / Share / Save actions.
- Expandable sources panel with per-source relevance scores.
- Local (browser-storage) saved-answers panel.
- Fixed: sparse-retrieval relevance now displays from the normalized
  `[0, 1]` score, not the raw unbounded BM25 score.
- Fixed: Copy/Share actions no longer fail silently when clipboard
  permission is denied.
- Premium README, `docs/` architecture set, CI, and community health
  files (this changelog included).

## 2026-07-28 — Product rebuild (FastAPI + Next.js)

- New FastAPI backend (`api/`) streaming answers over SSE.
- New Next.js frontend replacing the Streamlit app as the primary,
  end-user-facing product; Streamlit kept as the internal debug tool
  (index management, retrieval debug, statistics).

## 2026-07-27 — 2026-07-28 — Core RAG engine + Streamlit UI (20 milestones)

- Document ingestion (PDF/DOCX/TXT/HTML with OCR fallback), Uzbek
  legal-aware article chunking.
- Hybrid retrieval: FAISS (dense) + BM25 (sparse), fused and reranked by
  a cross-encoder.
- Grounded prompt construction + local LLM generation via Ollama.
- Streamlit UI: Home, Chat, Upload, Index management, Retrieval Debug,
  Statistics, Settings.
- Retrieval-quality evaluation suite (Precision@K, Recall@K, MRR, nDCG).
