"""
Text cleaning and Unicode normalization for ingested documents.

WHY THIS MODULE EXISTS
-----------------------
Raw text extracted from PDFs, DOCX, HTML, and plain-text files is messy in
ways that hurt both embedding quality and BM25 exact-term matching:
byte-order marks leaking into the string, CRLF line endings (all five
source law files are CRLF), runs of repeated whitespace from PDF layout
artifacts, non-printable control characters, and — critically for this
project — multiple valid Unicode encodings of visually identical
characters. `clean_text()` is the single choke point every loader routes
extracted text through before it reaches the database, so "clean" has one
consistent definition across the whole app instead of five slightly
different ad hoc implementations.

WHY UNICODE NORMALIZATION MATTERS HERE SPECIFICALLY
------------------------------------------------------
Unicode allows the same rendered glyph to be encoded multiple ways (e.g. a
precomposed accented letter vs. a base letter + combining accent mark).
Two byte-for-byte different strings that *look* identical will not match in
BM25 (exact token match) and may embed slightly differently. We apply NFC
(Canonical Composition) normalization — the standard choice for
search/matching use cases — so equivalent characters always collapse to
the same codepoint sequence.

Uzbek Latin script adds a real, non-hypothetical wrinkle: the "turned
comma" ⟨ʻ⟩ (U+02BB, used in the "oʻ"/"gʻ" digraphs — a genuinely distinct
sound from plain o/g) and the apostrophe ⟨ʼ⟩ (U+02BC, marking a glottal
stop, e.g. "maʼno") are two DIFFERENT letters with different linguistic
meaning — confirmed by inspecting the actual corpus, where both appear
correctly and distinctly. We deliberately do NOT collapse them into each
other. What we DO normalize are the common *fallback* substitutes that
appear when a document was typed without access to the correct Uzbek
keys — a plain ASCII apostrophe ⟨'⟩ or a right single quotation mark
⟨'⟩ — into the Uzbek apostrophe ⟨ʼ⟩, since that is overwhelmingly the more
common substitution in digitized Uzbek text. This is a documented
heuristic, not a proof: if a future document turns out to use ASCII ⟨'⟩ to
mean the digraph letter instead, this mapping will be wrong for that
document. See `UZBEK_APOSTROPHE_SUBSTITUTES` below to adjust it.

TIME / MEMORY COMPLEXITY
-------------------------
Every cleaning step is a single linear pass over the text (regex substitution
or `str.translate`), so the whole pipeline is O(n) time and O(n) additional
memory (Python strings are immutable; each step allocates a new string).
For the ~1MB source files here that's low-single-digit milliseconds per
document — irrelevant next to embedding/LLM costs later in the pipeline.

ADVANTAGES
-----------
- One function, one definition of "clean" — no drift between loaders.
- NFC normalization is a strict net improvement for search matching with
  essentially no downside for well-formed input.

DISADVANTAGES
--------------
- The apostrophe-substitution heuristic can misfire on documents whose
  ASCII-apostrophe convention differs from this corpus's.
- Aggressive whitespace collapsing discards some original formatting
  (e.g. deliberately indented sub-clauses) — acceptable here because
  chunking/embedding cares about textual content, not visual layout.

ALTERNATIVES CONSIDERED
-------------------------
- NFKD/NFKC (compatibility normalization): would also fold things like
  ligatures and width variants, but can be *lossy* for legal text (e.g.
  it can strip formatting distinctions meant to be preserved); NFC is the
  conservative, meaning-preserving choice.
- A full language-detection + spelling-correction pass: out of scope —
  this is cleanup, not a translation or OCR-correction pipeline.

BEST PRACTICES APPLIED
------------------------
- Normalize early, once, at the ingestion boundary — every downstream
  module (chunker, embedder, BM25 tokenizer) can assume clean, NFC text
  and never needs to re-implement this logic.
- Every transformation is a pure function of its input (no hidden state),
  making each step independently unit-testable.
"""

from __future__ import annotations

import re
import unicodedata

# Common ASCII/typographic substitutes for the Uzbek apostrophe (U+02BC),
# which marks a glottal stop (e.g. "maʼno", "eʼtirof"). See module
# docstring for why we do NOT also fold in the "turned comma" U+02BB.
UZBEK_APOSTROPHE_SUBSTITUTES = {
    "’": "ʼ",  # RIGHT SINGLE QUOTATION MARK
    "'": "ʼ",  # ASCII APOSTROPHE
}

# Zero-width and byte-order-mark characters that sometimes survive decoding
# (e.g. a BOM in the middle of a concatenated file, or a zero-width space
# copy-pasted from a web page) and are invisible but break exact matching.
_INVISIBLE_CHARS_PATTERN = re.compile("[﻿​‌‍]")

# Control characters (category Cc) other than the ones we intentionally
# keep: \n (newline) and \t (tab). Everything else in this category is a
# non-printable artifact, not real content.
_CONTROL_CHARS_KEEP = {"\n", "\t"}

# 3+ blank lines collapse to exactly one blank line (i.e. max one empty
# line between paragraphs) — keeps paragraph breaks without letting PDF
# extraction artifacts create pages of vertical whitespace.
_MULTI_BLANK_LINE_PATTERN = re.compile(r"\n[ \t]*\n[ \t]*(\n[ \t]*)+")

# Runs of horizontal whitespace (spaces/tabs, not newlines) collapse to one
# space — common in PDF text extraction where column layouts insert wide
# gaps of spaces.
_HORIZONTAL_WHITESPACE_RUN_PATTERN = re.compile(r"[ \t]{2,}")

# Trailing horizontal whitespace at the end of a line.
_TRAILING_WHITESPACE_PATTERN = re.compile(r"[ \t]+\n")


def normalize_line_endings(text: str) -> str:
    """Convert CRLF and lone CR line endings to LF.

    All five source law files use CRLF (Windows-style) line endings; a
    single canonical line ending downstream means every regex/split that
    assumes `\\n` works uniformly regardless of a document's origin OS.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_unicode(text: str) -> str:
    """Apply NFC (canonical composition) Unicode normalization.

    See module docstring for why NFC (not NFKC/NFKD) is the right choice
    here: it merges equivalent encodings of the same character without
    discarding meaning-bearing distinctions.
    """
    return unicodedata.normalize("NFC", text)


def normalize_uzbek_apostrophes(text: str) -> str:
    """Map common ASCII/typographic apostrophe substitutes to U+02BC.

    See `UZBEK_APOSTROPHE_SUBSTITUTES` and the module docstring for the
    linguistic reasoning and its limitations.
    """
    return text.translate(str.maketrans(UZBEK_APOSTROPHE_SUBSTITUTES))  # type: ignore[arg-type]  # str->str dict is valid at runtime; typeshed's dict invariance just can't express it


def remove_invisible_characters(text: str) -> str:
    """Strip BOMs and zero-width characters that can appear mid-string."""
    return _INVISIBLE_CHARS_PATTERN.sub("", text)


def remove_control_characters(text: str) -> str:
    """Strip non-printable control characters, keeping newline and tab.

    Iterates once over the string classifying each character by its
    Unicode general category; category "Cc" (control) characters other
    than \\n/\\t are artifacts (e.g. stray \\x00 bytes from a corrupted
    extraction) rather than real content.
    """
    return "".join(ch for ch in text if ch in _CONTROL_CHARS_KEEP or unicodedata.category(ch) != "Cc")


def collapse_whitespace(text: str) -> str:
    """Collapse redundant whitespace without destroying paragraph structure.

    - Multiple spaces/tabs in a row -> one space.
    - Trailing whitespace before a newline -> removed.
    - 3+ consecutive blank lines -> exactly one blank line.
    """
    text = _TRAILING_WHITESPACE_PATTERN.sub("\n", text)
    text = _HORIZONTAL_WHITESPACE_RUN_PATTERN.sub(" ", text)
    text = _MULTI_BLANK_LINE_PATTERN.sub("\n\n", text)
    return text.strip()


def clean_text(text: str) -> str:
    """Run the full cleaning pipeline in the order that makes each step valid.

    Order matters: line endings must be normalized before whitespace
    collapsing (which is newline-aware), invisible/control characters
    should be stripped before Unicode normalization (so they don't affect
    composition), and apostrophe substitution happens last so it operates
    on already-normalized text.
    """
    text = normalize_line_endings(text)
    text = remove_invisible_characters(text)
    text = remove_control_characters(text)
    text = normalize_unicode(text)
    text = normalize_uzbek_apostrophes(text)
    text = collapse_whitespace(text)
    return text
