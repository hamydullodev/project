# Deployment

<sub>[← Back to README](../README.md)</sub>

UzLaw AI is designed to run fully locally — there is no managed cloud
deployment target today. This doc covers running it reliably on a single
machine (a workstation, or a self-hosted server on your own network).

## The three processes

| Process | Command | Port | Required for |
|---|---|---|---|
| FastAPI backend | `python run_api.py` | `8000` | The product (frontend depends on it) |
| Next.js frontend | `npm run dev` (or `npm run build && npm start`) | `3000` | The product |
| Ollama | `ollama serve` | `11434` | Answer generation (every page except Streamlit's Statistics) |
| Streamlit debug tool *(optional)* | `python run.py` | `8501` | Index management / retrieval debug / statistics only |

`run_api.py` calls `uvicorn.run(...)` directly (uvicorn's own documented
way to start a server programmatically), while `run.py` shells out to
`streamlit run` via `subprocess` specifically because Streamlit's own
internals (`streamlit.web.bootstrap`) are not a documented, stable
public API.

## Production frontend build

Development mode (`npm run dev`) uses Turbopack with hot reload — fine
locally, not what you want for a longer-running deployment:

```bash
cd frontend
npm run build
npm start            # serves the production build on :3000
```

## Indexing

The index (FAISS + BM25 + SQLite metadata) is generated, not committed —
`indexes/*` and `data/*.db` are gitignored. On a fresh clone:

- Via the Streamlit tool: **Indeksni boshqarish** → **Indeksni qurish /
  yangilash** (always incremental; a full rebuild / delete is available
  behind a two-step confirmation since it's destructive).
- Or directly: `IndexingPipeline().sync()`.

Re-indexing an unchanged file is a fast no-op — content-hash-based
deduplication skips it.

## Health checks

`GET /api/health` reports Ollama connectivity, the configured
`LLM_MODEL`/`EMBEDDING_MODEL`, and corpus size (`total_documents`,
`total_chunks`) — useful as a liveness/readiness probe if you put this
behind a process supervisor.

## Error handling in production

Each layer defines its own typed exceptions rather than letting raw
library errors propagate to a user: `VectorStoreError` / `BM25IndexError`
for corrupted or missing indexes (the pipeline falls back to an empty
index rather than crashing), `DocumentLoadError` for broken/undecodable
source files, `LLMConnectionError` / `LLMModelNotFoundError` for an
unreachable or unpulled Ollama model — surfaced as a clear message (an
HTTP 503 from the API, or an in-UI message in Streamlit), never a raw
stack trace.

## What's intentionally out of scope

There is no authentication, multi-tenancy, or hosted/managed deployment
here — this is a single-user, local-first tool by design (per its own
"no cloud APIs, no external services after setup" premise). Adding those
would be a significant architectural change, not a deployment detail.
