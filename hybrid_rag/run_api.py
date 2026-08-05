"""
API entry point — mirrors `run.py`'s role for the Streamlit UI: one
documented command (`python run_api.py`) instead of remembering
`uvicorn api.main:app --host ... --port ...` by hand.

WHY `uvicorn.run(...)` DIRECTLY, UNLIKE `run.py`'S SUBPROCESS APPROACH
------------------------------------------------------------------------------
`run.py` shells out to `streamlit run` via `subprocess` specifically
because Streamlit's own internals (`streamlit.web.bootstrap`) are not a
documented, stable public API (see that file's docstring). Uvicorn is
different: `uvicorn.run(...)` IS its documented, official way to start a
server programmatically — used here directly, with no subprocess
indirection needed.
"""

from __future__ import annotations

import uvicorn

from api.config import get_api_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    settings = get_api_settings()
    logger.info(
        "Starting Hybrid RAG API on http://%s:%d (reload=%s)", settings.host, settings.port, settings.reload
    )
    uvicorn.run("api.main:app", host=settings.host, port=settings.port, reload=settings.reload)


if __name__ == "__main__":
    main()
