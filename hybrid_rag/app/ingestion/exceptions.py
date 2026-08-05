"""
Exception hierarchy for document loading failures.

WHY THIS MODULE EXISTS
-----------------------
The spec requires gracefully handling broken PDFs, empty files, and
encoding errors. "Gracefully" means the indexing pipeline (Milestone 10)
must be able to catch *one* exception type per failure category, log a
useful message, mark that single document as `status="failed"` in SQLite
with the reason recorded, and continue processing the rest of the corpus
— one bad file must never crash an entire indexing run.

A dedicated hierarchy (rather than raising bare `ValueError`/`OSError`)
lets calling code distinguish "this file's content is a legitimate reason
to skip it" (a `DocumentLoadError` subclass) from "something is actually
broken in the code" (any other exception, which should propagate and be
investigated, not silently swallowed).
"""

from __future__ import annotations


class DocumentLoadError(Exception):
    """Base class for all recoverable document-loading failures.

    The indexing pipeline catches this base class (not each subclass
    individually) when it wants to mark a document as failed and move on
    to the next file — see Milestone 10.
    """


class UnsupportedFileTypeError(DocumentLoadError):
    """Raised when a file's extension has no registered loader."""


class EmptyDocumentError(DocumentLoadError):
    """Raised when a file contains no extractable, non-whitespace text."""


class CorruptedDocumentError(DocumentLoadError):
    """Raised when a file's format is invalid or unparsable.

    E.g. a `.pdf` file that isn't actually a valid PDF, or a `.docx` file
    that isn't a valid zip/OOXML package.
    """
