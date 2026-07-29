"""
FastAPI backend for the Next.js frontend.

WHY THIS PACKAGE EXISTS
-----------------------
Every RAG stage (retrieval, reranking, compression, generation) already
lives in `app/` and is exercised end to end by the Streamlit UI
(`app/ui/`). That UI stays as the project's internal/debug tool
(Index management, Retrieval Debug, Statistics) — it isn't going away.
This package is a THIN HTTP layer over the exact same `app.rag.RAGPipeline`
the Streamlit UI already uses, so a separate, product-grade frontend
(built with Next.js/TypeScript, outside this Python project) can ask
questions and stream answers without embedding any Python.

Nothing in `app/` was designed around Streamlit specifically — every
module's public interface (`RAGPipeline.retrieve()`/`.ask_stream()`,
`MetadataRepository.get_statistics()`, `list_available_models()`) is
plain Python already. This package's entire job is translating that into
HTTP + JSON/SSE; it contains no RAG logic of its own.

WHY A SEPARATE TOP-LEVEL PACKAGE, NOT `app/api/`
-------------------------------------------------------
`app/` is the RAG core: it has no knowledge of HTTP, Streamlit, or any
particular frontend, and every module in it is importable and testable
without a web server running at all (see e.g. `tests/evaluation/`, which
imports `app.rag`, `app.retriever`, etc. directly with no UI involved).
Putting a web framework's routing/CORS/request-handling concerns inside
`app/` would blur that boundary. `api/` sits ALONGSIDE `app/` (imports
from it, never the other way around) for the same reason `app/ui/`
already does — a second consumer of `app/`'s public interface, not a
part of its internals.
"""
