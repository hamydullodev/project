"""
Statistics page: corpus, index, and process-level numbers at a glance.

WHY THIS PAGE READS THE FAISS SIDECAR DIRECTLY INSTEAD OF LOADING THE MODEL
----------------------------------------------------------------------------------
The spec asks for "embedding dimension" as one of this page's numbers. The
only way to know a `SentenceTransformer` model's output dimension is to
actually load it (Milestone 5's `EmbeddingModel.dimension`) — but that is a
real, multi-second-to-tens-of-seconds cost the FIRST time it happens in a
process, and it also means simply *viewing statistics* would force-load a
multi-hundred-MB model even for a user who only wants to check corpus size.
`FAISSVectorStore.save()` (Milestone 6) already writes the dimension into
its small JSON sidecar (`{vector_path}.meta.json`) as plain metadata, so
this page reads that file directly with `json.loads` — no `faiss.read_index`
call, no embedding model load, no Ollama dependency at all. This is also why
this is the one page in the app that works correctly with zero running
services: no Ollama, no cached `RAGPipeline` — just files on disk.

WHY MEMORY USAGE USES `resource.getrusage` INSTEAD OF `psutil`
--------------------------------------------------------------------
`psutil` is the more ergonomic, cross-platform way to read process memory,
but it isn't already a project dependency, and `resource.getrusage` (Python
stdlib, no install needed) reports the one number the spec actually asks
for — this process's peak resident set size — without adding a package for
a single metric. The trade-off, documented inline where it's used: `ru_maxrss`
units differ by OS (bytes on macOS/BSD, kilobytes on Linux) — a real,
long-standing inconsistency in the underlying `getrusage(2)` syscall across
platforms, not a bug in this code.
"""

from __future__ import annotations

import json
import resource
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from app.config import settings
from app.ui.components import render_page_header
from app.ui.resources import get_repo


def render() -> None:
    render_page_header("Korpus va indeks statistikasi.")

    repo = get_repo()
    stats = repo.get_statistics()

    _render_corpus_metrics(stats)
    st.divider()
    _render_law_breakdown(stats)
    st.divider()
    _render_index_metrics()
    st.divider()
    _render_memory_metrics()


def _render_corpus_metrics(stats: dict) -> None:
    st.subheader("📚 Korpus")
    col1, col2, col3 = st.columns(3)
    col1.metric("Hujjatlar", stats["total_documents"])
    col2.metric("Boʻlaklar (chunks)", stats["total_chunks"])
    avg_size = stats["avg_chunk_size_chars"]
    col3.metric("Oʻrtacha boʻlak hajmi", f"{avg_size:.0f} belgi" if avg_size else "—")


def _render_law_breakdown(stats: dict) -> None:
    st.subheader("⚖️ Qonunlar boʻyicha taqsimot")
    chunks_by_law = stats["chunks_by_law"]
    if not chunks_by_law:
        st.info("Hali hech qanday hujjat indekslanmagan.")
        return

    df = pd.DataFrame(
        [{"Qonun": law, "Boʻlaklar soni": count} for law, count in chunks_by_law.items()]
    )
    st.dataframe(df, width="stretch", hide_index=True)
    st.bar_chart(df.set_index("Qonun"))


def _render_index_metrics() -> None:
    st.subheader("🗂️ Indeks")

    dimension = _embedding_dimension()
    faiss_bytes, faiss_vectors = _faiss_index_size_and_count()
    bm25_bytes = _file_size(settings.bm25_path_resolved)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Embedding oʻlchami", dimension if dimension is not None else "—")
    col2.metric("FAISS vektorlar", faiss_vectors if faiss_vectors is not None else "—")
    col3.metric("FAISS hajmi", _format_bytes(faiss_bytes))
    col4.metric("BM25 hajmi", _format_bytes(bm25_bytes))

    if dimension is None:
        st.caption("Indeks hali qurilmagan — **Indeksni boshqarish** sahifasidan boshlang.")

    st.caption(
        f"SQLite metama'lumotlar bazasi: {_format_bytes(_file_size(settings.sqlite_path_resolved))} "
        f"— {settings.sqlite_path_resolved}"
    )


def _render_memory_metrics() -> None:
    st.subheader("💾 Xotira")
    rss_bytes = _process_memory_bytes()
    st.metric("Joriy jarayon xotirasi (RSS)", _format_bytes(rss_bytes) if rss_bytes is not None else "—")
    st.caption(
        "Streamlit serveri jarayonining joriy xotira sarfi — yuklangan embedding/reranker "
        "modellari va indekslar shu yerga kiradi. Model hali yuklanmagan boʻlsa, bu son "
        "keyinroq (Suhbat yoki Qidiruv tahlili sahifasi ochilgach) sezilarli oshadi."
    )


# -- helpers ------------------------------------------------------------------------


def _embedding_dimension() -> Optional[int]:
    meta_path = Path(f"{settings.vector_path_resolved}.meta.json")
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return meta.get("dimension")
    except (OSError, ValueError):
        return None


def _faiss_index_size_and_count() -> tuple[int, Optional[int]]:
    index_path = Path(f"{settings.vector_path_resolved}.faiss")
    meta_path = Path(f"{settings.vector_path_resolved}.meta.json")
    total_bytes = _file_size(index_path) + _file_size(meta_path)

    vector_count: Optional[int] = None
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            vector_count = len(meta.get("chunk_id_to_int", {}))
        except (OSError, ValueError):
            vector_count = None
    return total_bytes, vector_count


def _file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def _format_bytes(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"  # pragma: no cover - unreachable at this project's scale


def _process_memory_bytes() -> Optional[int]:
    try:
        ru_maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:  # noqa: BLE001 - a stats display must never crash the page
        return None
    # ru_maxrss is bytes on macOS/BSD, kilobytes on Linux - see module docstring.
    return ru_maxrss if sys.platform == "darwin" else ru_maxrss * 1024


# See app/ui/pages/chat.py's comment on this same guard for why it's here.
if __name__ == "__main__":
    render()
