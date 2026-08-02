"""
Unit tests for app.ui.pages.upload (Milestone 17).

Most tests call `_save_and_validate()` / `_process_uploads()` directly
with a small `FakeUploadedFile` stand-in (Streamlit's real
`UploadedFile` only exists inside a running app; duck-typing the two
attributes these functions actually use — `.name` and `.getvalue()` — is
simpler and faster than driving the full widget for logic that doesn't
need a browser or even a live Streamlit script run to verify). A few
integration tests at the bottom use `AppTest.from_file()` (see
test_ui_pages.py's docstring for why `from_file`, not `from_function`) to
confirm the actual `st.file_uploader` + button + results flow works
end-to-end, including `FileUploader.upload()`'s simulated file transfer.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.ui.pages.upload import UploadOutcome, _save_and_validate

PAGE_PATH = str(Path(__file__).resolve().parent.parent / "app" / "ui" / "pages" / "upload.py")


class FakeUploadedFile:
    """Duck-typed stand-in for Streamlit's UploadedFile — only `.name`
    and `.getvalue()` are used by `_save_and_validate`."""

    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


# ---------------------------------------------------------------------------
# _save_and_validate — core logic, no Streamlit runtime needed
# ---------------------------------------------------------------------------


def test_save_and_validate_saves_valid_txt_file(tmp_path: Path):
    target_dir = tmp_path / "uploaded"
    target_dir.mkdir()
    fake_file = FakeUploadedFile("test.txt", b"1-modda. Qonun matni.")

    outcome = _save_and_validate(fake_file, target_dir)

    assert outcome.status == "saved"
    assert outcome.overwritten is False
    assert outcome.size_bytes is not None
    assert (target_dir / "test.txt").exists()
    assert (target_dir / "test.txt").read_text(encoding="utf-8") == "1-modda. Qonun matni."


def test_save_and_validate_rejects_unsupported_extension(tmp_path: Path):
    target_dir = tmp_path / "uploaded"
    target_dir.mkdir()
    fake_file = FakeUploadedFile("malware.exe", b"not a real document")

    outcome = _save_and_validate(fake_file, target_dir)

    assert outcome.status == "rejected"
    assert outcome.error is not None
    assert not (target_dir / "malware.exe").exists()  # never even written to disk


def test_save_and_validate_rejects_and_removes_empty_file(tmp_path: Path):
    target_dir = tmp_path / "uploaded"
    target_dir.mkdir()
    fake_file = FakeUploadedFile("empty.txt", b"   \n  ")

    outcome = _save_and_validate(fake_file, target_dir)

    assert outcome.status == "failed"
    assert not (target_dir / "empty.txt").exists()  # broken upload cleaned up


def test_save_and_validate_rejects_corrupted_pdf(tmp_path: Path):
    target_dir = tmp_path / "uploaded"
    target_dir.mkdir()
    fake_file = FakeUploadedFile("broken.pdf", b"%PDF-1.4 this is not a real pdf body")

    outcome = _save_and_validate(fake_file, target_dir)

    assert outcome.status == "failed"
    assert not (target_dir / "broken.pdf").exists()


def test_save_and_validate_marks_overwrite(tmp_path: Path):
    target_dir = tmp_path / "uploaded"
    target_dir.mkdir()
    (target_dir / "existing.txt").write_text("Eski matn.", encoding="utf-8")

    fake_file = FakeUploadedFile("existing.txt", b"Yangi matn.")
    outcome = _save_and_validate(fake_file, target_dir)

    assert outcome.status == "saved"
    assert outcome.overwritten is True
    assert (target_dir / "existing.txt").read_text(encoding="utf-8") == "Yangi matn."


def test_save_and_validate_restores_previous_file_on_failed_overwrite(tmp_path: Path):
    """The critical safety behavior: overwriting a working file with a
    BROKEN new upload must not destroy the working original."""
    target_dir = tmp_path / "uploaded"
    target_dir.mkdir()
    original_content = "1-modda. Ishlaydigan asl hujjat."
    (target_dir / "law.txt").write_text(original_content, encoding="utf-8")

    fake_file = FakeUploadedFile("law.txt", b"   ")  # empty-after-cleaning -> fails validation
    outcome = _save_and_validate(fake_file, target_dir)

    assert outcome.status == "failed"
    # The original, working file must still be there, unchanged.
    assert (target_dir / "law.txt").read_text(encoding="utf-8") == original_content


# ---------------------------------------------------------------------------
# _process_uploads — batch behavior (needs a live Streamlit script context
# for st.progress, so these still go through AppTest via the page below,
# not called directly)
# ---------------------------------------------------------------------------


def test_upload_outcome_model_fields():
    outcome = UploadOutcome(file_name="a.txt", status="saved", size_bytes=10)
    assert outcome.error is None
    assert outcome.overwritten is False


# ---------------------------------------------------------------------------
# Full page integration (AppTest)
# ---------------------------------------------------------------------------


def test_upload_page_renders_without_errors():
    at = AppTest.from_file(PAGE_PATH)
    at.run()

    assert not at.exception


def test_upload_page_shows_no_button_without_files():
    at = AppTest.from_file(PAGE_PATH)
    at.run()

    upload_buttons = [b for b in at.button if "yuklash" in b.label.lower()]
    assert len(upload_buttons) == 0


def test_upload_page_end_to_end_valid_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app.config import settings as app_settings

    monkeypatch.setattr(app_settings, "documents_path", str(tmp_path))

    at = AppTest.from_file(PAGE_PATH)
    at.run()

    at.get("file_uploader")[0].upload("qonun.txt", b"1-modda. Sinov qonuni matni.", "text/plain").run()

    upload_buttons = [b for b in at.button if "yuklash" in b.label.lower()]
    assert len(upload_buttons) == 1

    upload_buttons[0].click().run()

    assert not at.exception
    success_text = " ".join(s.value for s in at.success)
    assert "muvaffaqiyatli saqlandi" in success_text
    assert (tmp_path / "uploaded" / "qonun.txt").exists()


def test_upload_page_shows_index_link_after_successful_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings as app_settings

    monkeypatch.setattr(app_settings, "documents_path", str(tmp_path))

    at = AppTest.from_file(PAGE_PATH)
    at.run()
    at.get("file_uploader")[0].upload("qonun.txt", b"1-modda. Sinov qonuni matni.", "text/plain").run()
    [b for b in at.button if "yuklash" in b.label.lower()][0].click().run()

    assert not at.exception
    page_links = at.get("page_link")
    assert any("Indeksni boshqarish" in (link.label or "") for link in page_links)
