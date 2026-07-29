"""
Unit tests for app.ingestion (cleaning + loaders).

Uses pytest's `tmp_path` to synthesize small fixture files for each format
in-place, so the tests don't depend on external sample files and run fast
without network access.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion import (
    CorruptedDocumentError,
    EmptyDocumentError,
    UnsupportedFileTypeError,
    load_document,
)
from app.ingestion.cleaning import (
    clean_text,
    collapse_whitespace,
    normalize_uzbek_apostrophes,
)

# ---------------------------------------------------------------------------
# cleaning.py
# ---------------------------------------------------------------------------


def test_normalize_line_endings_and_collapse_whitespace():
    raw = "1-modda.\r\nMatn.\r\n\r\n\r\n\r\n2-modda.\r\n"
    cleaned = clean_text(raw)
    assert "\r" not in cleaned
    # 4 blank lines collapse to exactly one.
    assert "\n\n\n" not in cleaned
    assert "1-modda." in cleaned and "2-modda." in cleaned


def test_collapse_whitespace_preserves_paragraph_breaks():
    text = "Paragraph one.\n\nParagraph two."
    assert collapse_whitespace(text) == text


def test_horizontal_whitespace_runs_collapse():
    text = "So'z1     so'z2\tso'z3"
    result = collapse_whitespace(text)
    assert "  " not in result


def test_ascii_apostrophe_normalized_to_uzbek_glottal_stop():
    # ASCII ' and typographic ' should both become the Uzbek modifier
    # letter apostrophe U+02BC (glottal stop marker).
    assert normalize_uzbek_apostrophes("ma'no") == "maʼno"
    assert normalize_uzbek_apostrophes("ma’no") == "maʼno"


def test_turned_comma_digraph_letter_untouched():
    # The oʻ/gʻ digraph letter (U+02BB) must NOT be altered by cleaning —
    # it is a distinct letter, not a substitute apostrophe.
    text = "Oʻzbekiston"
    assert clean_text(text) == text


def test_control_characters_stripped():
    text = "Toza matn\x00bilan\x07 ifloslangan"
    cleaned = clean_text(text)
    assert "\x00" not in cleaned
    assert "\x07" not in cleaned


def test_bom_and_zero_width_chars_removed():
    text = "﻿Matn boshi​va davomi"
    cleaned = clean_text(text)
    assert "﻿" not in cleaned
    assert "​" not in cleaned


# ---------------------------------------------------------------------------
# loaders.py — TXT
# ---------------------------------------------------------------------------


def test_load_txt_utf8(tmp_path: Path):
    path = tmp_path / "law.txt"
    path.write_text("1-modda. Oʻzbekiston qonuni.", encoding="utf-8")

    doc = load_document(path)
    assert doc.file_type == "txt"
    assert doc.num_pages == 1
    assert "1-modda" in doc.full_text


def test_load_txt_utf8_bom(tmp_path: Path):
    path = tmp_path / "law_bom.txt"
    path.write_bytes(b"\xef\xbb\xbf" + "Matn BOM bilan".encode("utf-8"))

    doc = load_document(path)
    assert "﻿" not in doc.full_text
    assert "Matn BOM bilan" in doc.full_text


def test_load_txt_windows1251_fallback(tmp_path: Path):
    """A file that isn't valid UTF-8 should fall back through the encoding
    chain instead of raising, since legacy Cyrillic-Uzbek sources use
    Windows-1251."""
    path = tmp_path / "law_cyrillic.txt"
    path.write_bytes("Узбекистон конуни".encode("windows-1251"))

    doc = load_document(path)
    assert "Узбекистон" in doc.full_text


def test_load_txt_empty_file_raises(tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_text("   \n\n  ", encoding="utf-8")

    with pytest.raises(EmptyDocumentError):
        load_document(path)


def test_unsupported_extension_raises(tmp_path: Path):
    path = tmp_path / "law.xyz"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError):
        load_document(path)


# ---------------------------------------------------------------------------
# loaders.py — DOCX
# ---------------------------------------------------------------------------


def test_load_docx(tmp_path: Path):
    docx = pytest.importorskip("docx")
    path = tmp_path / "law.docx"
    d = docx.Document()
    d.add_paragraph("1-modda. Fuqarolik huquqi.")
    d.add_paragraph("2-modda. Boshqa qoida.")
    d.save(str(path))

    doc = load_document(path)
    assert doc.file_type == "docx"
    assert doc.num_pages == 1  # DOCX has no real page boundaries
    assert "1-modda" in doc.full_text
    assert "2-modda" in doc.full_text


def test_load_docx_corrupted_raises(tmp_path: Path):
    pytest.importorskip("docx")
    path = tmp_path / "fake.docx"
    path.write_bytes(b"this is not a real docx zip file")

    with pytest.raises(CorruptedDocumentError):
        load_document(path)


# ---------------------------------------------------------------------------
# loaders.py — HTML
# ---------------------------------------------------------------------------


def test_load_html(tmp_path: Path):
    pytest.importorskip("bs4")
    path = tmp_path / "law.html"
    path.write_text(
        "<html><head><style>.x{color:red}</style></head>"
        "<body><script>evil()</script>"
        "<h1>1-modda</h1><p>Qonun matni.</p></body></html>",
        encoding="utf-8",
    )

    doc = load_document(path)
    assert doc.file_type == "html"
    assert "1-modda" in doc.full_text
    assert "Qonun matni" in doc.full_text
    assert "evil()" not in doc.full_text
    assert "color:red" not in doc.full_text


# ---------------------------------------------------------------------------
# loaders.py — PDF
# ---------------------------------------------------------------------------


def test_load_pdf_native_text(tmp_path: Path):
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "law.pdf"

    pdf = fitz.open()
    page1 = pdf.new_page()
    page1.insert_text((72, 72), "1-modda. Birinchi sahifa.")
    page2 = pdf.new_page()
    page2.insert_text((72, 72), "2-modda. Ikkinchi sahifa.")
    pdf.save(str(path))
    pdf.close()

    doc = load_document(path)
    assert doc.file_type == "pdf"
    assert doc.num_pages == 2
    assert "1-modda" in doc.pages[0]
    assert "2-modda" in doc.pages[1]


def test_load_pdf_corrupted_raises(tmp_path: Path):
    pytest.importorskip("fitz")
    path = tmp_path / "fake.pdf"
    path.write_bytes(b"%PDF-1.4 this is not a real pdf body")

    with pytest.raises(CorruptedDocumentError):
        load_document(path)


def test_load_pdf_blank_page_ocr_fallback_no_crash(tmp_path: Path):
    """A page with no text layer (e.g. a blank/scanned page) must not
    crash loading even if it yields no text — OCR either extracts
    something or degrades gracefully to an empty string + warning."""
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "scanned.pdf"

    pdf = fitz.open()
    pdf.new_page()  # a page with zero text content
    page2 = pdf.new_page()
    page2.insert_text((72, 72), "3-modda. Matnli sahifa.")
    pdf.save(str(path))
    pdf.close()

    doc = load_document(path)
    assert doc.num_pages == 2
    assert "3-modda" in doc.pages[1]
