"""
Top-level chunking orchestration: LoadedDocument -> list[ChunkDraft].

WHY THIS MODULE EXISTS
-----------------------
`legal_parser.py` knows how to find article boundaries in Uzbek legal-code
text; `loaders.py` knows how to get clean per-page text out of a file. This
module is where those combine into the actual unit the rest of the system
retrieves and cites: a chunk. It owns three responsibilities the spec asks
for explicitly:

  1. Prefer legal-structure-aware splitting (one article = one semantic
     unit) over blind character splitting, falling back to the latter only
     when a document doesn't look like a structured legal code (e.g. a
     future generic upload with no "N-modda." markers at all) — this is
     what makes "support adding new documents later without changing
     code" true even for non-legal-code documents.
  2. Further split any article whose body still exceeds `chunk_size` using
     `RecursiveCharacterTextSplitter`, with configurable character- or
     token-based length measurement and overlap, while every resulting
     sub-chunk keeps the parent article's full metadata.
  3. Attach the exact metadata fields the spec requires per chunk:
     document name, page number, section, article number, law name, and a
     chunk id (the id itself is assigned later by the indexing pipeline
     once it knows the owning `document_id` — see `ChunkDraft` below).

WHY CHUNKDRAFT INSTEAD OF ChunkRecord DIRECTLY
--------------------------------------------------
`app.database.models.ChunkRecord` requires `id` and `document_id`, neither
of which the chunker can know — `document_id` is assigned when the
indexing pipeline (Milestone 10) creates the document's row in SQLite,
which happens independently of chunking. `ChunkDraft` carries everything
the chunker DOES know; the pipeline turns each draft into a `ChunkRecord`
with `ChunkRecord.make_id(document_id, draft.chunk_index)`.

PAGE NUMBER MAPPING
-----------------------
For paginated formats (PDF), `PageMapper` converts a character offset
within the noise-stripped, page-joined text back into a 1-based page
number, using the same page-joining scheme (`"\\n\\n".join(pages)`) that
`parse_legal_structure()` receives its input from — so an article's
`start_offset` (computed in legal_parser.py) lands in the right page
bucket. For non-paginated formats (TXT/DOCX/HTML, or any document with
only one page), every chunk's `page_number` is `None`, matching
`ChunkRecord.page_number: Optional[int]`.

TIME / MEMORY COMPLEXITY
-------------------------
O(n) in document length for legal-structure parsing and noise stripping
(see legal_parser.py), plus O(n) for the character-splitting pass over any
article exceeding `chunk_size` (each character-splitter invocation is
itself linear in the text it's given). Overall chunking a single document
is O(document length); memory is O(document length) for the resulting
chunk texts (each character of the original document appears in at most
`ceil(chunk_size / (chunk_size - chunk_overlap))` chunks, a small constant
determined by the overlap ratio, not by document size).

ADVANTAGES
-----------
- Citations are always article-accurate: the fallback splitter only ever
  operates *within* one article's text, never across an article boundary.
- One function (`chunk_document`) is the single entry point the indexing
  pipeline calls, regardless of whether the input turned out to be a
  structured legal code or a generic document — the caller doesn't need
  to know or care which path was taken internally.

DISADVANTAGES
--------------
- The approximate token counter (see `approximate_token_count`) is a
  regex-based estimate, not the embedding model's real BPE tokenization —
  adequate for sizing chunks, not for guaranteeing an exact token budget.
- Page-number attribution for an article that itself spans a page
  boundary uses the article's *start* offset only — a chunk whose article
  begins on page 4 and continues onto page 5 is attributed entirely to
  page 4. Acceptable for citation purposes (the reader can always see the
  full article) and irrelevant for the current corpus (single-page TXT
  sources).

ALTERNATIVES CONSIDERED
-------------------------
- Fixed-size sliding-window chunking over the raw document (ignoring
  structure entirely): simpler, but produces chunks that routinely span
  two articles, making "always cite article numbers" unenforceable.
- Token-exact chunking via the real embedding model's tokenizer: more
  precise, but couples this module to a specific model being loaded
  (expensive) just to chunk text; left as a future upgrade path once
  Milestone 5's embedder exists, by swapping the `length_function` passed
  to `RecursiveCharacterTextSplitter`.

BEST PRACTICES APPLIED
------------------------
- Every chunk's `char_count` is stored at write time (not recomputed on
  every read), matching `ChunkRecord.char_count`.
- The whole pipeline degrades gracefully: zero articles found -> plain
  splitting; an article under `chunk_size` -> exactly one chunk, no
  unnecessary splitter invocation.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from pydantic import BaseModel

from app.config import settings
from app.ingestion.legal_parser import (
    ParsedArticle,
    deduplicate_articles,
    parse_legal_structure,
    strip_legal_noise,
)
from app.ingestion.loaders import LoadedDocument
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Approximates "words and punctuation tokens" as a stand-in for real BPE
# subword tokens — close enough to size chunks sensibly without loading an
# actual tokenizer model during ingestion. See module docstring.
_APPROX_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)

# A law title line is expected to be short; anything longer is almost
# certainly the start of body prose, not a document title.
_MAX_LAW_NAME_LENGTH = 150


def approximate_token_count(text: str) -> int:
    """Estimate a token count by counting word and punctuation tokens.

    Deliberately not exact BPE tokenization (see module docstring) — used
    only to size chunks when `CHUNKING_STRATEGY=token`.
    """
    return len(_APPROX_TOKEN_PATTERN.findall(text))


def _length_function(strategy: str) -> Callable[[str], int]:
    return len if strategy == "character" else approximate_token_count


class ChunkDraft(BaseModel):
    """Everything the chunker knows about one chunk, before it has an id.

    The indexing pipeline (Milestone 10) turns each draft into a
    `ChunkRecord` once it has assigned `document_id`.
    """

    chunk_index: int
    text: str
    char_count: int
    law_name: Optional[str] = None
    article_number: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[int] = None


class PageMapper:
    """Maps a character offset (into the page-joined text) to a page number.

    Built from the same list of per-page strings and the same `"\\n\\n"`
    join scheme that produced the text `parse_legal_structure()` parsed,
    so offsets computed there resolve to the correct page here.
    """

    def __init__(self, pages: list[str]) -> None:
        self._boundaries: list[int] = []
        offset = 0
        for page_text in pages:
            self._boundaries.append(offset)
            offset += len(page_text) + 2  # +2 for the "\n\n" join separator
        self._single_page = len(pages) <= 1

    def page_for_offset(self, char_offset: int) -> Optional[int]:
        """Return the 1-based page number containing `char_offset`.

        Returns `None` for single-page documents (TXT/DOCX/HTML, or a
        1-page PDF) — page numbers are only meaningful when a document
        genuinely has more than one page.
        """
        if self._single_page:
            return None
        # Find the last boundary <= char_offset via linear scan. A binary
        # search would be O(log p) vs O(p) here, but p (page count) is at
        # most a few hundred even for a very long PDF, so the simpler
        # linear scan's constant-factor simplicity wins in practice.
        page_index = 0
        for i, boundary in enumerate(self._boundaries):
            if boundary <= char_offset:
                page_index = i
            else:
                break
        return page_index + 1  # 1-based


def _extract_law_name(full_text: str, fallback: str) -> str:
    """Take the document's first non-empty line as its law name.

    Falls back to `fallback` (typically the filename stem) if the first
    line is missing, empty, or implausibly long to be a title (i.e. it's
    almost certainly body prose, not a heading).
    """
    for line in full_text.split("\n"):
        stripped = line.strip()
        if stripped:
            if len(stripped) <= _MAX_LAW_NAME_LENGTH:
                return stripped
            break
    return fallback


def _split_long_text(text: str, chunk_size: int, chunk_overlap: int, strategy: str) -> list[str]:
    """Split `text` into pieces no longer than `chunk_size`, with overlap.

    Uses LangChain's `RecursiveCharacterTextSplitter`, which tries to
    split on paragraph breaks first, then sentence-ish boundaries, then
    words, only falling back to splitting mid-word if nothing else fits —
    this keeps sub-chunks readable instead of cutting at an arbitrary
    character position.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=_length_function(strategy),
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def _chunks_from_articles(
    articles: list[ParsedArticle],
    law_name: str,
    page_mapper: PageMapper,
    chunk_size: int,
    chunk_overlap: int,
    strategy: str,
) -> list[ChunkDraft]:
    length_fn = _length_function(strategy)
    drafts: list[ChunkDraft] = []
    chunk_index = 0

    for article in articles:
        page_number = page_mapper.page_for_offset(article.start_offset)
        pieces = (
            [article.text]
            if length_fn(article.text) <= chunk_size
            else _split_long_text(article.text, chunk_size, chunk_overlap, strategy)
        )
        for piece in pieces:
            drafts.append(
                ChunkDraft(
                    chunk_index=chunk_index,
                    text=piece,
                    char_count=len(piece),
                    law_name=law_name,
                    article_number=article.article_number,
                    section=article.section,
                    page_number=page_number,
                )
            )
            chunk_index += 1

    return drafts


def _chunks_from_plain_text(
    full_text: str,
    law_name: str,
    page_mapper: PageMapper,
    chunk_size: int,
    chunk_overlap: int,
    strategy: str,
) -> list[ChunkDraft]:
    """Fallback path for documents with no detectable legal-article structure."""
    pieces = _split_long_text(full_text, chunk_size, chunk_overlap, strategy)
    drafts: list[ChunkDraft] = []
    search_from = 0

    for i, piece in enumerate(pieces):
        # Best-effort offset lookup for page attribution: find where this
        # piece occurs starting from the last match, so repeated text
        # (e.g. overlap between consecutive pieces) still advances forward
        # instead of resolving every piece to the first page.
        offset = full_text.find(piece[:50], search_from)
        if offset == -1:
            offset = search_from
        search_from = offset + 1

        drafts.append(
            ChunkDraft(
                chunk_index=i,
                text=piece,
                char_count=len(piece),
                law_name=law_name,
                article_number=None,
                section=None,
                page_number=page_mapper.page_for_offset(offset),
            )
        )
    return drafts


def chunk_document(
    loaded_doc: LoadedDocument,
    file_name: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    strategy: Optional[str] = None,
) -> list[ChunkDraft]:
    """Chunk a loaded document into metadata-rich `ChunkDraft`s.

    Tries legal-structure-aware chunking first (article-boundary-safe);
    falls back to plain character/token splitting if the document doesn't
    contain any `N-modda.` article markers at all.
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap
    strategy = strategy or settings.chunking_strategy

    fallback_law_name = file_name.rsplit(".", 1)[0]
    law_name = _extract_law_name(loaded_doc.full_text, fallback_law_name)

    noiseless_pages = [strip_legal_noise(p) for p in loaded_doc.pages]
    page_mapper = PageMapper(noiseless_pages)
    joined_text = "\n\n".join(noiseless_pages)

    articles = parse_legal_structure(joined_text)
    articles = deduplicate_articles(articles)

    if articles:
        drafts = _chunks_from_articles(
            articles, law_name, page_mapper, chunk_size, chunk_overlap, strategy
        )
    else:
        logger.info(
            "No legal article structure detected in %s; falling back to plain chunking",
            file_name,
        )
        drafts = _chunks_from_plain_text(
            joined_text, law_name, page_mapper, chunk_size, chunk_overlap, strategy
        )

    logger.info(
        "Chunked %s: %d chunk(s) from %d article(s), strategy=%s, size=%d, overlap=%d",
        file_name,
        len(drafts),
        len(articles),
        strategy,
        chunk_size,
        chunk_overlap,
    )
    return drafts
