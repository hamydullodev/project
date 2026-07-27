"""
Project entry point.

WHY THIS MODULE EXISTS
-----------------------
`streamlit run app/ui/Home.py` works, but launching Streamlit directly
skips any startup checks we might want (config validation, directory
creation, a friendly error if `.env` is malformed). `run.py` is the single
documented command users run (`python run.py`), and it delegates to
Streamlit under the hood via `streamlit.web.cli`. This mirrors the common
pattern of having one unambiguous entry point at the project root instead
of asking users to remember an internal file path.

Right now (Milestone 1) there is no UI yet, so this just validates that
configuration loads correctly and prints a summary — useful as a smoke
test after `pip install -r requirements.txt`. Later milestones will extend
this to actually launch the Streamlit app.
"""

from __future__ import annotations

import sys

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    logger.info("Hybrid RAG — Uzbek Law | configuration check")
    logger.info("Project root:        %s", settings.project_root)
    logger.info("LLM model (Ollama):  %s", settings.llm_model)
    logger.info("Embedding model:     %s", settings.embedding_model)
    logger.info("Reranker model:      %s", settings.reranker_model)
    logger.info("Chunk size/overlap:  %d / %d", settings.chunk_size, settings.chunk_overlap)
    logger.info("Top-K / Rerank-K:    %d / %d", settings.top_k, settings.rerank_top_k)
    logger.info("Documents path:      %s", settings.documents_path_resolved)
    logger.info("Vector index path:   %s", settings.vector_path_resolved)
    logger.info("BM25 index path:     %s", settings.bm25_path_resolved)
    logger.info("SQLite path:         %s", settings.sqlite_path_resolved)

    if not settings.documents_path_resolved.exists() or not any(
        settings.documents_path_resolved.rglob("*")
    ):
        logger.warning(
            "No documents found under %s — nothing to index yet.",
            settings.documents_path_resolved,
        )

    logger.info(
        "Configuration OK. UI entry point isn't built yet (that's a later "
        "milestone) — for now this command only validates setup."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - top-level entry point: log and exit non-zero
        logger.exception("Startup failed")
        sys.exit(1)
