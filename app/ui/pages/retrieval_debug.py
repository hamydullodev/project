"""
Retrieval debug page: inspect exactly how a query was retrieved and ranked.

WHY THIS PAGE EXISTS
-----------------------
Every other page treats retrieval as an internal step on the way to an
answer — this page treats it as the thing being examined. It runs
`RAGPipeline.retrieve()` (Milestone 14) and shows EVERY stage's output:
every candidate hybrid search found (with its raw and normalized dense/
sparse scores), every candidate's reranker score, and exactly which ones
context compression kept versus dropped and why. For a hybrid-retrieval
system built specifically to be educational, being able to answer "why
did THIS chunk rank where it did" concretely, with real numbers, is the
point of the whole exercise — not just get a good final answer, but be
able to see the machinery that produced it.

WHY THIS PAGE STILL REQUIRES A WORKING RAGPipeline (AND THEREFORE OLLAMA)
EVEN THOUGH IT NEVER CALLS THE LLM
--------------------------------------------------------------------------------
`retrieve()` never touches the LLM — only the embedding model, BM25
index, and reranker. Strictly, this page COULD be built on a lighter
resource that skips `OllamaLLM` entirely. It deliberately isn't: this
page calls `get_pipeline()`, the SAME cached `RAGPipeline` the Chat page
uses (Milestone 16), rather than constructing an independent
retriever+reranker combination. Reusing the identical, already-tested
`RAGPipeline.retrieve()` method means there is exactly one implementation
of "how retrieval works" in the whole app — this page can never quietly
drift from what Chat actually does, which would be a real risk if this
page reimplemented retrieval logic separately just to avoid Ollama as a
dependency. Since Ollama is already a hard requirement for this entire
project (not something usable without it), the cost of this choice is
low: in practice, anyone able to meaningfully use this page already has
Ollama running for the rest of the app anyway.

WHY EVERY RERANKED CANDIDATE IS SHOWN, NOT JUST THE FINAL "KEPT" ONES
--------------------------------------------------------------------------
`context.reranked` (the full list BEFORE compression) is shown in its
entirety, each row labeled with its compression outcome — "kept",
"dropped as a duplicate", or "dropped for the context budget" — rather
than only showing the final surviving chunks. Seeing what got filtered
OUT, and specifically why, is exactly the transparency a debug page needs
to provide; showing only survivors would hide half of what context
compression (Milestone 11) actually does.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.llm import LLMConnectionError, LLMModelNotFoundError
from app.rag import EmptyQueryError
from app.rag.pipeline import RetrievalContext
from app.reranker import RerankedResult
from app.ui.components import render_chunk_card, render_page_header
from app.ui.resources import get_pipeline

_STATUS_KEPT = "✅ Saqlangan"
_STATUS_DUPLICATE = "🔁 Takror (dedup)"
_STATUS_BUDGET = "✂️ Byudjet chegarasi"


def render() -> None:
    render_page_header("Qidiruv natijalarini batafsil tahlil qilish: dense/sparse/rerank ballari.")
    st.caption(
        "Bu sahifa javob generatsiya qilmaydi — faqat qidiruv bosqichlarini (dense, sparse, "
        "rerank, kontekst siqish) koʻrsatadi."
    )

    try:
        pipeline = get_pipeline()
    except (LLMConnectionError, LLMModelNotFoundError) as e:
        st.error(f"❌ Til modeliga ulanib boʻlmadi: {e}")
        st.info("Ollama ishga tushirilganligiga ishonch hosil qiling: `ollama serve`")
        return

    query = st.text_input(
        "Sinov soʻrovi",
        placeholder="Masalan: Mehnat shartnomasini qanday bekor qilish mumkin?",
    )

    if query and st.button("🔍 Qidirish", type="primary"):
        try:
            with st.spinner("Qidirilmoqda..."):
                context = pipeline.retrieve(query)
        except EmptyQueryError:
            st.warning("Iltimos, savol kiriting.")
            return

        _show_context(context)


def _status_map(context: RetrievalContext) -> dict[str, str]:
    status: dict[str, str] = {}
    for chunk in context.compression.kept:
        status[chunk.chunk_id] = _STATUS_KEPT
    for chunk in context.compression.dropped_duplicate:
        status[chunk.chunk_id] = _STATUS_DUPLICATE
    for chunk in context.compression.dropped_budget:
        status[chunk.chunk_id] = _STATUS_BUDGET
    return status


def _show_context(context: RetrievalContext) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Dense/Sparse natijalar", len(context.hybrid_results))
    col2.metric("Rerankdan keyin", len(context.reranked))
    col3.metric("Saqlangan (LLM ga boradi)", len(context.compression.kept))

    if not context.reranked:
        st.warning("Hech qanday natija topilmadi.")
        return

    st.divider()
    st.subheader("📊 Ball taqqoslash jadvali")
    status_map = _status_map(context)
    st.dataframe(_build_table(context.reranked, status_map), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📄 Boʻlaklar (batafsil)")
    for i, chunk in enumerate(context.reranked, start=1):
        render_chunk_card(i, chunk, status_label=status_map.get(chunk.chunk_id))


def _build_table(reranked: list[RerankedResult], status_map: dict[str, str]) -> pd.DataFrame:
    rows = [
        {
            "#": i,
            "Qonun": chunk.law_name or "—",
            "Modda": chunk.article_number or "—",
            "Dense": round(chunk.dense_score, 4) if chunk.dense_score is not None else None,
            "Sparse": round(chunk.sparse_score, 4) if chunk.sparse_score is not None else None,
            "Combined": round(chunk.combined_score, 4),
            "Rerank": round(chunk.reranker_score, 4),
            "Holat": status_map.get(chunk.chunk_id, "—"),
        }
        for i, chunk in enumerate(reranked, start=1)
    ]
    return pd.DataFrame(rows)


# See app/ui/pages/chat.py's comment on this same guard for why it's here.
if __name__ == "__main__":
    render()
