"""
Query preprocessing: the first step of the question-answering pipeline.

WHY THIS MODULE EXISTS
-----------------------
A user's raw typed question needs the same cleanup as document text
before either the embedder or BM25 sees it — encoding artifacts,
stray whitespace, and (critically for this project) inconsistent
apostrophe characters. This module is the query-side counterpart to
`app.ingestion.cleaning.clean_text`, applied at question-answering time
rather than at indexing time.

WHY REUSING `clean_text` HERE IS NOT OPTIONAL
-----------------------------------------------------
This is the single most important reason this module exists rather than
the caller just passing the raw query straight to the retriever. Recall
from `app.ingestion.cleaning` (Milestone 3): the Uzbek glottal-stop letter
ʼ (U+02BC) is what gets indexed, but most users typing on a standard
keyboard will type a plain ASCII apostrophe `'` instead (e.g. "ma'no"
instead of "maʼno"). BM25 (Milestone 7) matches EXACT tokens — if the
query keeps the ASCII apostrophe while the index holds U+02BC, that word
simply never matches lexically, with no error or warning, just quietly
worse retrieval. Running every query through the exact same `clean_text`
pipeline used at index time (same NFC normalization, same apostrophe
mapping) guarantees a query and a matching document normalize to
IDENTICAL token sequences.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
------------------------------------------------
No query expansion, rewriting, or reformulation (e.g. asking an LLM to
rephrase the question before retrieval, or generating multiple query
variants to retrieve with). Those are legitimate, more advanced RAG
techniques, but they require calling the LLM (Milestone 13, not yet
built when this module was designed) BEFORE retrieval even starts, adding
a full generation round-trip of latency to every question. This module
sticks to cheap, deterministic, always-safe cleanup — the same
"normalize, don't rewrite" philosophy `clean_text` already applies to
documents.

TIME / MEMORY COMPLEXITY
-------------------------
O(n) in query length for cleaning (a handful of regex passes — see
`clean_text`'s docstring), O(1) for the length check/truncation. A
question is a few dozen to a few hundred characters; this entire module
runs in well under a millisecond.

ADVANTAGES
-----------
- Guarantees query/document tokenization consistency for BM25 — the
  concrete, measurable reason this module exists rather than being
  "just call clean_text inline wherever needed."
- Rejects genuinely empty input early, with a clear, specific exception,
  before any retrieval work is attempted.

DISADVANTAGES
--------------
- Cannot fix a poorly-WORDED question (e.g. one missing key legal
  terminology) — it normalizes characters, it doesn't improve the
  question's substance. That class of improvement is what query
  expansion/rewriting (not implemented here, see above) would address.

ALTERNATIVES CONSIDERED
-------------------------
- LLM-based query rewriting/expansion: a valid future upgrade once
  Milestone 13's local LLM exists, at the cost of added latency per
  query; deliberately deferred rather than built prematurely.
- Skipping preprocessing and relying on the tokenizer alone to be
  forgiving: rejected because `tokenize()` (Milestone 7) does exact
  Unicode-codepoint matching — it has no fuzziness to lean on if the
  query and index disagree on which apostrophe character to use.

BEST PRACTICES APPLIED
------------------------
- Reuses `clean_text` rather than reimplementing a parallel cleaning
  routine — one definition of "clean," used identically at both index
  time and query time (the same principle `tokenizer.py` applies for
  tokenization itself).
- Truncation (for pathologically long input) is logged, not silent —
  a user pasting in a huge block of text by mistake gets a warning
  trail in `logs/app.log`, not silently mangled results.
"""

from __future__ import annotations

from app.config import settings
from app.ingestion.cleaning import clean_text
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmptyQueryError(Exception):
    """Raised when a query is empty, whitespace-only, or empty after cleaning."""


def preprocess_query(raw_query: str) -> str:
    """Clean and validate a raw user question before it reaches retrieval.

    Applies the same normalization pipeline used at index time (NFC
    Unicode normalization, apostrophe-substitute mapping, whitespace
    collapsing — see `clean_text`'s docstring) so a query tokenizes
    identically to how matching document text was tokenized, then
    enforces a maximum length. Raises `EmptyQueryError` for empty or
    whitespace-only input.
    """
    cleaned = clean_text(raw_query)

    if not cleaned:
        raise EmptyQueryError("Query is empty after cleaning.")

    if len(cleaned) > settings.max_query_length:
        logger.warning(
            "Query length %d exceeds MAX_QUERY_LENGTH=%d; truncating.",
            len(cleaned),
            settings.max_query_length,
        )
        cleaned = cleaned[: settings.max_query_length].rstrip()

    return cleaned
