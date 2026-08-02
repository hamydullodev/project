"""
Upload page: add new source documents (PDF, DOCX, TXT, HTML).

WHY THIS PAGE ONLY SAVES FILES — IT NEVER INDEXES THEM
------------------------------------------------------------
The spec lists "Upload Documents" and "Rebuild Index" as two SEPARATE
pages, and this page respects that boundary deliberately: its entire job
is getting files safely onto disk under `documents/uploaded/`, validated
enough to know they're at least parseable. Actually chunking, embedding,
and indexing them is comparatively slow (Milestone 10's own measurements:
tens of seconds for a handful of files) and is Milestone 18's Index
management page's job, triggered explicitly by the user. Coupling upload
to indexing would force every upload — even someone adding ten files in
quick succession — to eat that cost per file rather than once, batched,
when the user is actually ready. This page ends with a direct link to
Index management instead, so the two concerns stay separately
triggerable but easy to chain together.

WHY EACH FILE IS VALIDATED (LOADED) IMMEDIATELY AFTER SAVING
--------------------------------------------------------------------
Saving raw bytes to disk always "succeeds" — a corrupted PDF, a
password-protected DOCX, or a genuinely empty file all write to disk
without error. Without a validation step, a user uploading a broken file
wouldn't find out until they later run indexing (Milestone 18) — at which
point the connection between "that batch upload three days ago" and "this
cryptic indexing error" is far less obvious than an immediate, specific
message right after the upload attempt. This page calls
`app.ingestion.load_document()` (Milestone 3) on each saved file right
away and reports success/failure per file — the same "gracefully handle
broken input, keep processing the rest of the batch" principle
`IndexingPipeline` (Milestone 10) applies, just moved earlier in the
pipeline where the feedback is more actionable.

WHY A FAILED VALIDATION RESTORES THE PREVIOUS FILE INSTEAD OF DELETING IT
---------------------------------------------------------------------------------
Uploading a file with the same name as an existing one overwrites it —
simple, predictable behavior. But if the NEW content fails validation,
naively deleting the file on failure would destroy a perfectly good
PREVIOUSLY-uploaded document just because its replacement was broken.
This page reads the old file's bytes into memory before overwriting, and
restores them if the new upload fails validation — the failed upload
reports an error, but a working file that was already there is never
silently lost as a side effect. Only a genuinely NEW file's broken upload
gets removed (nothing to restore).

WHY st.file_uploader NEEDS NO CUSTOM DRAG-AND-DROP OR PROGRESS CODE
--------------------------------------------------------------------------
`st.file_uploader(..., accept_multiple_files=True)` natively supports
drag-and-drop and multi-file selection, and shows its own upload progress
in the browser as bytes transfer to the Streamlit server — the spec's
"Drag & Drop" and part of "Progress bar" requirements are satisfied by
the widget itself, not custom code. The `st.progress()` bar this page
DOES add covers the separate, server-side step of saving and validating
each file after it arrives (real, sometimes-slow work — a scanned PDF may
trigger OCR, Milestone 3), which the browser's own upload progress can't
represent since it doesn't know about that server-side work at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import streamlit as st
from pydantic import BaseModel

from app.config import settings
from app.ingestion import DocumentLoadError, load_document
from app.ingestion.loaders import SUPPORTED_EXTENSIONS
from app.ui.components import render_page_header


class UploadOutcome(BaseModel):
    """What happened to one uploaded file — mirrors the spirit of
    `DocumentIndexOutcome` (Milestone 10), scoped to this page's own
    save-and-validate step rather than full indexing."""

    file_name: str
    status: Literal["saved", "failed", "rejected"]
    error: str | None = None
    overwritten: bool = False
    size_bytes: int | None = None


def render() -> None:
    render_page_header("Yangi hujjatlarni yuklash: PDF, DOCX, TXT, HTML.")
    st.markdown(
        "Fayllarni shu yerga sudrab tashlang yoki tanlang. Bir nechta faylni "
        "bir vaqtning oʻzida yuklashingiz mumkin."
    )
    st.caption(
        "⚠️ Yuklangan hujjatlar avtomatik ravishda qidiruvga qoʻshilmaydi — "
        "buning uchun keyinroq **Indeksni boshqarish** sahifasidan foydalaning."
    )

    allowed_types = sorted(ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS)
    uploaded_files = st.file_uploader(
        "Hujjatlarni tanlang",
        type=allowed_types,
        accept_multiple_files=True,
    )

    if uploaded_files and st.button(f"📤 {len(uploaded_files)} ta faylni yuklash", type="primary"):
        results = _process_uploads(uploaded_files)
        _show_results(results)


def _process_uploads(uploaded_files: list) -> list[UploadOutcome]:
    target_dir = settings.documents_path_resolved / "uploaded"
    target_dir.mkdir(parents=True, exist_ok=True)

    progress = st.progress(0.0, text="Boshlanmoqda...")
    results: list[UploadOutcome] = []

    for i, uploaded_file in enumerate(uploaded_files):
        progress.progress(i / len(uploaded_files), text=f"Qayta ishlanmoqda: {uploaded_file.name}")
        results.append(_save_and_validate(uploaded_file, target_dir))

    progress.progress(1.0, text="Tayyor!")
    return results


def _save_and_validate(uploaded_file, target_dir: Path) -> UploadOutcome:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return UploadOutcome(
            file_name=uploaded_file.name,
            status="rejected",
            error=f"Qoʻllab-quvvatlanmaydigan format: {suffix}",
        )

    target_path = target_dir / uploaded_file.name
    previous_bytes = target_path.read_bytes() if target_path.exists() else None
    overwritten = previous_bytes is not None

    target_path.write_bytes(uploaded_file.getvalue())

    try:
        load_document(target_path)
    except DocumentLoadError as e:
        if previous_bytes is not None:
            target_path.write_bytes(previous_bytes)  # restore the working previous version
        else:
            target_path.unlink(missing_ok=True)  # nothing to restore - remove the broken upload
        return UploadOutcome(file_name=uploaded_file.name, status="failed", error=str(e))

    return UploadOutcome(
        file_name=uploaded_file.name,
        status="saved",
        overwritten=overwritten,
        size_bytes=target_path.stat().st_size,
    )


def _show_results(results: list[UploadOutcome]) -> None:
    saved = [r for r in results if r.status == "saved"]
    failed = [r for r in results if r.status == "failed"]
    rejected = [r for r in results if r.status == "rejected"]

    if saved:
        st.success(f"✅ {len(saved)} ta fayl muvaffaqiyatli saqlandi:")
        for r in saved:
            note = " _(mavjud fayl almashtirildi)_" if r.overwritten else ""
            st.write(f"- **{r.file_name}** — {r.size_bytes:,} bayt{note}")

    if failed:
        st.error(f"❌ {len(failed)} ta fayl yuklanmadi:")
        for r in failed:
            st.write(f"- **{r.file_name}**: {r.error}")

    if rejected:
        st.warning(f"⚠️ {len(rejected)} ta fayl qoʻllab-quvvatlanmaydi:")
        for r in rejected:
            st.write(f"- **{r.file_name}**: {r.error}")

    if saved:
        st.divider()
        st.info("Yuklangan hujjatlarni qidiruvga qoʻshish uchun quyidagi sahifaga oʻting:")
        # Deferred import to avoid a circular import with app.ui.navigation
        # (which imports this module's `render` to build its own st.Page
        # object) — see navigation.py's module docstring, and home.py for
        # the identical pattern.
        from app.ui.navigation import index_page

        st.page_link(index_page, label="Indeksni boshqarish sahifasiga oʻtish", icon="🗂️")


# See app/ui/pages/chat.py's comment on this same guard for why it's here.
if __name__ == "__main__":
    render()
