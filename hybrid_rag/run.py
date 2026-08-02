"""
Project entry point.

WHY THIS MODULE EXISTS
-----------------------
`streamlit run app/ui/streamlit_app.py` works directly, but launching
Streamlit that way skips any startup checks worth running first (config
validation, a friendly error if `.env` is malformed) and requires
remembering an internal file path. `run.py` is the single documented
command users run (`python run.py`) — it validates configuration, then
launches Streamlit as a subprocess pointed at the real entry script,
giving one unambiguous top-level command regardless of how the UI's
internal files are organized.

WHY SUBPROCESS RATHER THAN CALLING STREAMLIT'S INTERNAL API DIRECTLY
--------------------------------------------------------------------------
Streamlit does not officially support being launched programmatically
from arbitrary Python code in a stable way — its own internals
(`streamlit.web.bootstrap`, etc.) are not a documented public API and
have changed across versions. Shelling out to `streamlit run` via
`subprocess` — the same command a user would type themselves — uses
Streamlit exactly as it's designed to be used and documented, at the
minor cost of a second process instead of one. Any extra command-line
arguments passed to `python run.py` are forwarded straight through to
`streamlit run` (e.g. `python run.py --server.port 8502`), so nothing
about Streamlit's own CLI is hidden or reimplemented.
"""

from __future__ import annotations

import subprocess
import sys

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

STREAMLIT_APP_PATH = settings.project_root / "app" / "ui" / "streamlit_app.py"


def check_configuration() -> None:
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

    if not settings.documents_path_resolved.exists() or not any(settings.documents_path_resolved.rglob("*")):
        logger.warning(
            "No documents found under %s — nothing to index yet.",
            settings.documents_path_resolved,
        )

    logger.info("Configuration OK.")


def launch_streamlit(extra_args: list[str]) -> int:
    logger.info("Launching Streamlit UI: %s", STREAMLIT_APP_PATH)
    command = [sys.executable, "-m", "streamlit", "run", str(STREAMLIT_APP_PATH), *extra_args]
    result = subprocess.run(command)
    return result.returncode


def main() -> None:
    check_configuration()
    exit_code = launch_streamlit(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - top-level entry point: log and exit non-zero
        logger.exception("Startup failed")
        sys.exit(1)
