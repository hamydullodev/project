"""
Settings page: view current configuration and check system connectivity.

WHY THIS PAGE IS READ-ONLY (NOT A LIVE SETTINGS EDITOR)
------------------------------------------------------------
`app.config.settings` (Milestone 1) is loaded once from `.env` at process
startup via `pydantic-settings`, validated, and cached
(`@lru_cache`-backed `get_settings()`) — there is no mechanism to change
a running process's configuration or to safely rewrite `.env` from
inside the app without risking corrupting it mid-edit or leaving the
running process's cached `Settings` object out of sync with the file on
disk. Rather than build that machinery (parsing, validating, and
atomically rewriting `.env`, plus a way to signal every cached resource
—`get_repo()`, and every model loaded in later milestones — to reload)
for a personal, single-user local tool, this page shows the CURRENT
configuration clearly and tells the user exactly what to do to change it
(edit `.env`, restart the app) — simpler, and just as effective for how
this project is actually used.

WHY THE OLLAMA CONNECTIVITY CHECK IS A BUTTON, NOT ALWAYS-ON
------------------------------------------------------------------
Home page (Milestone 15) already shows a lightweight, always-visible
Ollama status badge. This page's version is explicitly button-triggered
so it can show more detail (the full list of locally available models)
without that heavier information being fetched and re-rendered on every
single page interaction/rerun — the user asks for it when they actually
want to check.
"""

from __future__ import annotations

import streamlit as st

from app.config import settings
from app.ui.components import render_page_header
from app.ui.resources import check_ollama_status


def render() -> None:
    render_page_header("Joriy konfiguratsiya va tizim ulanishlarini tekshirish.")

    st.info(
        "Sozlamalarni oʻzgartirish uchun loyihaning `.env` faylini tahrirlang va "
        "ilovani qayta ishga tushiring. Bu sahifa faqat joriy qiymatlarni koʻrsatadi."
    )

    _render_llm_settings()
    _render_embedding_settings()
    _render_reranker_settings()
    _render_chunking_and_retrieval_settings()
    _render_storage_paths()
    _render_connectivity_check()


def _render_llm_settings() -> None:
    with st.expander("🤖 Til modeli (LLM)", expanded=True):
        col1, col2 = st.columns(2)
        col1.write(f"**Model:** `{settings.llm_model}`")
        col1.write(f"**Ollama manzili:** `{settings.ollama_base_url}`")
        col2.write(f"**Temperature:** `{settings.llm_temperature}`")
        col2.write(f"**Max tokens:** `{settings.llm_max_tokens}`")


def _render_embedding_settings() -> None:
    with st.expander("🧬 Embedding modeli"):
        col1, col2 = st.columns(2)
        col1.write(f"**Model:** `{settings.embedding_model}`")
        col2.write(f"**Qurilma (device):** `{settings.embedding_device}`")


def _render_reranker_settings() -> None:
    with st.expander("🎯 Reranker modeli"):
        col1, col2 = st.columns(2)
        col1.write(f"**Model:** `{settings.reranker_model}`")
        col2.write(f"**Qurilma (device):** `{settings.reranker_device}`")


def _render_chunking_and_retrieval_settings() -> None:
    with st.expander("✂️ Boʻlaklash (chunking) va qidiruv"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Chunk hajmi:** `{settings.chunk_size}`")
            st.write(f"**Chunk overlap:** `{settings.chunk_overlap}`")
            st.write(f"**Strategiya:** `{settings.chunking_strategy}`")
            st.write(f"**Max soʻrov uzunligi:** `{settings.max_query_length}`")
        with col2:
            st.write(f"**TOP_K:** `{settings.top_k}`")
            st.write(f"**RERANK_TOP_K:** `{settings.rerank_top_k}`")
            st.write(f"**Dense/Sparse vazn:** `{settings.dense_weight}` / `{settings.sparse_weight}`")
            st.write(f"**Max kontekst (belgilar):** `{settings.max_context_chars}`")


def _render_storage_paths() -> None:
    with st.expander("💾 Fayl yoʻllari"):
        st.write(f"**Hujjatlar:** `{settings.documents_path_resolved}`")
        st.write(f"**FAISS indeks:** `{settings.vector_path_resolved}`")
        st.write(f"**BM25 indeks:** `{settings.bm25_path_resolved}`")
        st.write(f"**SQLite baza:** `{settings.sqlite_path_resolved}`")
        st.write(f"**Loglar:** `{settings.log_dir_resolved}`")


def _render_connectivity_check() -> None:
    st.subheader("Ulanishni tekshirish")
    if st.button("🔌 Ollama ulanishini tekshirish"):
        with st.spinner("Tekshirilmoqda..."):
            ollama_ok, models, error = check_ollama_status()

        if ollama_ok:
            st.success(f"✅ Ollama serveriga muvaffaqiyatli ulanildi. {len(models)} ta model mavjud:")
            for model in models:
                marker = "✓" if model == settings.llm_model else "•"
                st.write(f"{marker} `{model}`")
            if settings.llm_model not in models:
                st.warning(
                    f"⚠️ Sozlamalardagi model `{settings.llm_model}` hozircha yuklab olinmagan. "
                    f"Yuklash uchun: `ollama pull {settings.llm_model}`"
                )
        else:
            st.error(f"❌ Ollama serveriga ulanib boʻlmadi: {error}")


# See app/ui/pages/chat.py's comment on this same guard for why it's here.
if __name__ == "__main__":
    render()
