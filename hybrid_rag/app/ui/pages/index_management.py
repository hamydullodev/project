"""
Index management page: build, update, rebuild, or delete the search index.

WHY "Build Index" / "Update Index" / "Incremental Indexing" ARE ONE BUTTON
--------------------------------------------------------------------------------
The spec lists these as three separate buttons, but they map to exactly
ONE underlying operation: `IndexingPipeline.sync()` (Milestone 10). That
milestone's central design decision was that `sync()` is ALWAYS
incremental by construction — an empty index means every file looks
"new" (so it behaves like "Build"), a populated index with a few changed
files only reprocesses those (so it behaves like "Update"/"Incremental").
There is no separate code path for any of these three cases; giving them
three separate buttons that all call the identical function would imply
a distinction that doesn't exist and would be actively misleading. One
button, honestly labeled to explain it covers all three, is more
accurate than three buttons pretending to differ.

WHY REBUILD AND DELETE REQUIRE AN EXPLICIT CONFIRMATION STEP
--------------------------------------------------------------------
Both are hard to casually undo: "Rebuild" wipes the current index and
metadata before re-processing everything from scratch (source documents
are untouched, but the index is briefly empty and the operation takes
real time — tens of seconds for this project's corpus); "Delete" wipes
the index and metadata with no re-indexing at all. Per this project's own
operating principle around consequential actions, a single misplaced
click on either shouldn't be able to immediately wipe real, possibly
slow-to-rebuild state — both require a first click that shows a warning
and asks for a second, explicit confirming click before anything actually
happens.

WHY EVERY INDEX-MODIFYING ACTION CLEARS THE CACHED RAGPipeline
------------------------------------------------------------------------
`app.ui.resources.get_pipeline()` (used by the Chat page, Milestone 16)
caches a `RAGPipeline` — including its own in-memory FAISS/BM25 state —
for the life of the process. If this page changes what's on disk without
telling that cache, a Chat session would keep answering from
now-stale in-memory data with no visible error. Every action here calls
`invalidate_query_pipeline_cache()` afterward so the next chat message
picks up the fresh index — see that function's own docstring for the
full reasoning.
"""

from __future__ import annotations

import streamlit as st

from app.ingestion.pipeline import IndexingSummary
from app.ui.components import render_page_header
from app.ui.resources import get_indexing_pipeline, get_repo, invalidate_query_pipeline_cache

CONFIRM_REBUILD_KEY = "confirm_rebuild_index"
CONFIRM_DELETE_KEY = "confirm_delete_index"


def render() -> None:
    render_page_header("Qidiruv indeksini qurish, yangilash yoki oʻchirish.")

    _render_current_status()
    st.divider()
    _render_sync_section()
    st.divider()
    _render_rebuild_section()
    st.divider()
    _render_delete_section()


def _render_current_status() -> None:
    repo = get_repo()
    stats = repo.get_statistics()

    col1, col2, col3 = st.columns(3)
    col1.metric("Hujjatlar", stats["total_documents"])
    col2.metric("Boʻlaklar (chunks)", stats["total_chunks"])
    col3.metric("Baza hajmi", f"{stats['db_size_bytes'] / 1024 / 1024:.1f} MB")

    documents = repo.list_documents()
    if documents:
        with st.expander(f"📄 Hujjatlar roʻyxati ({len(documents)} ta)"):
            for doc in documents:
                status_icon = {"indexed": "✅", "failed": "❌", "pending": "⏳"}.get(doc.status, "❓")
                st.write(
                    f"{status_icon} **{doc.file_name}** — {doc.num_chunks} ta boʻlak, {doc.law_name or '—'}"
                )
                if doc.status == "failed" and doc.error_message:
                    st.caption(f"Xato: {doc.error_message}")


def _render_sync_section() -> None:
    st.subheader("🔨 Qurish / Yangilash")
    st.caption(
        "Hujjatlar papkasini skanerlaydi: yangi va oʻzgargan fayllarni qayta indekslaydi, "
        "oʻzgarmagan fayllarni oʻtkazib yuboradi. Birinchi marta ishga tushirilganda — bu "
        "toʻliq indeks qurish, keyingi safarlarda — qoʻshimcha (incremental) yangilash "
        "boʻladi. Alohida tugmalarga ehtiyoj yoʻq, chunki bu bitta amal."
    )
    if st.button("🔨 Indeksni qurish / yangilash", type="primary"):
        with st.spinner("Hujjatlar indekslanmoqda..."):
            summary = get_indexing_pipeline().sync()
        invalidate_query_pipeline_cache()
        _show_summary(summary)


def _render_rebuild_section() -> None:
    st.subheader("♻️ Nolldan qayta qurish")
    st.caption("Butun indeksni oʻchirib, barcha hujjatlarni qaytadan indekslaydi.")

    if not st.session_state.get(CONFIRM_REBUILD_KEY, False):
        if st.button("♻️ Nolldan qayta qurish"):
            st.session_state[CONFIRM_REBUILD_KEY] = True
            st.rerun()
    else:
        st.warning(
            "⚠️ Bu amal joriy indeksni oʻchirib, barcha hujjatlarni qaytadan qayta ishlaydi. Davom etasizmi?"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Ha, qayta qurish", type="primary"):
                st.session_state[CONFIRM_REBUILD_KEY] = False
                with st.spinner("Indeks nolldan qurilmoqda..."):
                    summary = get_indexing_pipeline().rebuild()
                invalidate_query_pipeline_cache()
                _show_summary(summary)
        with col2:
            if st.button("❌ Bekor qilish"):
                st.session_state[CONFIRM_REBUILD_KEY] = False
                st.rerun()


def _render_delete_section() -> None:
    st.subheader("🗑️ Indeksni oʻchirish")
    st.caption(
        "Barcha metama'lumotlar va vektorlarni oʻchiradi (manba hujjatlar " "`documents/` papkasida qoladi)."
    )

    if not st.session_state.get(CONFIRM_DELETE_KEY, False):
        if st.button("🗑️ Indeksni oʻchirish"):
            st.session_state[CONFIRM_DELETE_KEY] = True
            st.rerun()
    else:
        st.error(
            "⚠️ Bu amalni ortga qaytarib boʻlmaydi. Indeks va barcha metama'lumotlar oʻchiriladi. Davom etasizmi?"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Ha, oʻchirish", type="primary"):
                st.session_state[CONFIRM_DELETE_KEY] = False
                with st.spinner("Oʻchirilmoqda..."):
                    get_indexing_pipeline().delete_all()
                invalidate_query_pipeline_cache()
                st.success("✅ Indeks toʻliq oʻchirildi.")
                st.rerun()
        with col2:
            if st.button("❌ Bekor qilish", key="cancel_delete"):
                st.session_state[CONFIRM_DELETE_KEY] = False
                st.rerun()


def _show_summary(summary: IndexingSummary) -> None:
    st.success(
        f"✅ Tayyor! {summary.total_files_scanned} ta fayl koʻrib chiqildi "
        f"({summary.duration_seconds:.1f} soniyada)."
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Indekslandi", summary.total_indexed)
    col2.metric("Oʻzgarmagan", summary.total_skipped_unchanged)
    col3.metric("Nusxa", summary.total_skipped_duplicate)
    col4.metric("Xato", summary.total_failed)

    failed_outcomes = [o for o in summary.outcomes if o.status == "failed"]
    if failed_outcomes:
        with st.expander(f"❌ Xatoliklar ({len(failed_outcomes)} ta)"):
            for outcome in failed_outcomes:
                st.write(f"- **{outcome.file_path}**: {outcome.error_message}")


# See app/ui/pages/chat.py's comment on this same guard for why it's here.
if __name__ == "__main__":
    render()
