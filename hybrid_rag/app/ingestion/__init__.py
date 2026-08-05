"""Document loading, cleaning, normalization, and chunking."""

from app.ingestion.chunker import ChunkDraft, chunk_document
from app.ingestion.cleaning import clean_text
from app.ingestion.exceptions import (
    CorruptedDocumentError,
    DocumentLoadError,
    EmptyDocumentError,
    UnsupportedFileTypeError,
)
from app.ingestion.legal_parser import ParsedArticle, parse_legal_structure
from app.ingestion.loaders import (
    ANALYSIS_SUPPORTED_EXTENSIONS,
    LoadedDocument,
    load_document,
    load_for_analysis,
)
from app.ingestion.pipeline import DocumentIndexOutcome, IndexingPipeline, IndexingSummary

__all__ = [
    "clean_text",
    "load_document",
    "load_for_analysis",
    "ANALYSIS_SUPPORTED_EXTENSIONS",
    "LoadedDocument",
    "DocumentLoadError",
    "UnsupportedFileTypeError",
    "EmptyDocumentError",
    "CorruptedDocumentError",
    "chunk_document",
    "ChunkDraft",
    "parse_legal_structure",
    "ParsedArticle",
    "IndexingPipeline",
    "IndexingSummary",
    "DocumentIndexOutcome",
]
