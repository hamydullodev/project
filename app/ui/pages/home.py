"""
Home page: system overview, corpus stats, quick status, quick links.

WHY THIS PAGE EXISTS
-----------------------
The spec lists "Home" as the first required page. Its job is orientation:
a user (or developer) landing on the app should immediately see whether
the system is actually ready to use (is Ollama running? is a corpus
indexed?) and how to get to what they actually want (asking a question,
adding documents) — without needing to already understand the project's
internal architecture.
"""

from __future__ import annotations

import streamlit as st

from app.config import settings
from app.ui.components import render_page_header, status_badge
from app.ui.resources import check_ollama_status, get_repo


def render() -> None:
    render_page_header("Mahalliy, xavfsiz va oflayn ishlaydigan yuridik hujjatlar boʻyicha AI yordamchi.")

    st.markdown(
        "Bu tizim Oʻzbekiston Respublikasi qonun hujjatlari asosida savollaringizga "
        "javob beradi — barcha maʼlumotlar faqat sizning kompyuteringizda saqlanadi, "
        "hech qanday maʼlumot tashqi serverlarga yuborilmaydi."
    )

    st.divider()
    _render_status_row()
    st.divider()
    _render_corpus_overview()
    st.divider()
    _render_quick_links()


def _render_status_row() -> None:
    st.subheader("Tizim holati")
    col1, col2, col3 = st.columns(3)

    repo = get_repo()
    stats = repo.get_statistics()
    ollama_ok, models, _ = check_ollama_status()

    with col1:
        st.metric("Hujjatlar", stats["total_documents"])
    with col2:
        st.metric("Matn boʻlaklari (chunks)", stats["total_chunks"])
    with col3:
        st.metric("Ollama modeli", settings.llm_model)

    status_col1, status_col2 = st.columns(2)
    with status_col1:
        status_badge(
            stats["total_chunks"] > 0,
            "Indeks tayyor — savol berishingiz mumkin",
            "Indeks boʻsh — avval hujjatlarni indekslang",
        )
    with status_col2:
        status_badge(
            ollama_ok,
            f"Ollama ulandi: {len(models)} ta model mavjud",
            "Ollama serveriga ulanib boʻlmadi — `ollama serve` ishga tushiring",
        )


def _render_corpus_overview() -> None:
    st.subheader("Indekslangan qonunlar")
    repo = get_repo()
    stats = repo.get_statistics()
    chunks_by_law = stats.get("chunks_by_law") or {}

    if not chunks_by_law:
        st.warning(
            "Hozircha hech qanday hujjat indeklanmagan. "
            "**Hujjat yuklash** yoki **Indeksni boshqarish** sahifasidan boshlang."
        )
        return

    for law_name, chunk_count in chunks_by_law.items():
        st.markdown(f"- **{law_name}** — {chunk_count} ta boʻlak")


def _render_quick_links() -> None:
    # Deferred import to avoid a circular import with app.ui.navigation
    # (which imports this module's `render` to build its Chat/Upload/
    # Index st.Page objects) — see navigation.py's module docstring.
    from app.ui.navigation import chat_page, index_page, upload_page

    st.subheader("Tezkor havolalar")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.page_link(chat_page, label="Savol berish", icon="💬")
    with col2:
        st.page_link(upload_page, label="Hujjat yuklash", icon="📤")
    with col3:
        st.page_link(index_page, label="Indeksni qurish", icon="🗂️")


# See app/ui/pages/chat.py's comment on this same guard for why it's
# here — lets this file run standalone (streamlit run / AppTest.from_file)
# without double-rendering when app.ui.navigation imports it normally.
if __name__ == "__main__":
    render()
