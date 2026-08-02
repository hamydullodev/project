"""
Context compression: shrinking reranked chunks into a clean LLM prompt budget.

WHY THIS MODULE EXISTS
-----------------------
`RerankerModel` (Milestone 9) hands back `RERANK_TOP_K` chunks sorted by
relevance — but "the top K most relevant chunks" is not automatically
"the best possible context to hand an LLM." Two problems remain even
after reranking:

  1. **Redundancy.** `CHUNK_OVERLAP` (Milestone 4) means adjacent
     sub-chunks of a long article deliberately share text at their
     boundary — that overlap is a feature for retrieval (it stops an
     answer from being cut exactly at a chunk boundary), but if BOTH
     overlapping sub-chunks end up in the top-K, the LLM prompt now
     contains the same sentence twice. Worse, an article split into
     several sub-chunks can have more than one of its pieces surface
     independently in hybrid retrieval, each scored well on its own
     merits, producing redundant context that wastes prompt space
     without adding new information.
  2. **Budget.** Nothing upstream enforces a hard cap on total context
     size. `RERANK_TOP_K` chunks at up to `CHUNK_SIZE` characters each
     could, in the worst case, exceed a reasonable prompt budget,
     especially on a smaller local LLM with a limited context window.

`compress_context()` addresses both: drop chunks that are highly
redundant with an already-kept, higher-ranked chunk, then enforce a
total character budget by dropping the lowest-ranked remaining chunks
first if still over budget.

WHY JACCARD SIMILARITY OVER WORD SETS (NOT A HEAVIER METHOD)
--------------------------------------------------------------------
Redundancy detection needs to answer one question — "is this chunk's
text substantially the same information as a chunk I already kept?" —
for at most `RERANK_TOP_K` items (a handful), not the whole corpus. Word-
set Jaccard similarity (`|intersection| / |union|` of each chunk's token
set) is O(chunk length) per comparison, needs no additional model or
dependency, and is directly interpretable ("60% of the distinct words
overlap") — appropriate precision for a small, cheap, explainable filter
applied to a handful of already-relevance-filtered candidates. It reuses
`tokenize()` (Milestone 7) rather than a separate word-splitting routine,
for the same "one definition, used everywhere" reason as elsewhere in
this project.

TIME / MEMORY COMPLEXITY
-------------------------
- Deduplication: O(k²) chunk-pair comparisons for k reranked candidates
  (k = `RERANK_TOP_K`, typically single digits), each comparison O(chunk
  length) to tokenize and compute Jaccard similarity — negligible in
  absolute terms (k is small by construction, this never runs against
  the full corpus).
- Budget enforcement: O(k) — a single pass accumulating character counts
  in rank order.
- Memory: O(k · chunk length) — holds only the already-small reranked
  set, never anything corpus-sized.

ADVANTAGES
-----------
- Strictly reduces prompt size/noise without needing an LLM call itself
  (unlike LLM-based summarization, the other common "context
  compression" technique) — zero added latency, fully deterministic.
- Every dropped chunk is categorized (`dropped_duplicate` vs
  `dropped_budget`) and returned, not just discarded — exactly the
  transparency the Retrieval Debug page (Milestone 18) needs to show
  "why wasn't this chunk used" rather than context compression being an
  invisible black box.

DISADVANTAGES
--------------
- Word-set Jaccard similarity has no notion of word order or semantics —
  two chunks with the same words in a very different order (unlikely for
  this project's overlap-driven redundancy, but possible in principle)
  could be flagged as more similar than they really are, and semantically
  paraphrased duplicates (rare given both chunks come from the SAME
  source corpus, not independently authored) wouldn't be caught at all.
- The character budget is a blunt instrument: it drops whole chunks
  rather than intelligently truncating a chunk's least-relevant sentence
  — appropriate given a chunk is already the atomic, citation-bearing
  unit for this project ("always cite article numbers" requires a whole,
  intact chunk, not an arbitrarily truncated fragment of one).

ALTERNATIVES CONSIDERED
-------------------------
- LLM-based extractive/abstractive summarization of each chunk before
  prompting: the standard heavier-weight "context compression" technique
  in RAG literature; deliberately not used here because it requires an
  LLM call (Milestone 13 didn't exist yet when this was built) per chunk,
  adding significant latency for a project whose corpus produces chunks
  already close to the target size, not needing aggressive summarization.
- Embedding-based (cosine similarity) redundancy detection instead of
  Jaccard: would reuse the embedding model already loaded (Milestone 5),
  but adds a model inference cost to a step whose entire purpose is
  cheap, fast cleanup right before prompting; word-set Jaccard achieves
  the same practical goal (catch near-identical overlapping text) at
  effectively zero cost.

BEST PRACTICES APPLIED
------------------------
- Deduplication always compares a candidate against KEPT chunks only
  (not all other candidates), so the result is well-defined regardless of
  how many chunks happen to be mutually similar to each other — the
  highest-ranked chunk in a redundant cluster always survives.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.config import settings
from app.reranker.cross_encoder import RerankedResult
from app.retriever.tokenizer import tokenize
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CompressionResult(BaseModel):
    """Full provenance of what context compression kept and dropped, and why."""

    kept: list[RerankedResult]
    dropped_duplicate: list[RerankedResult] = []
    dropped_budget: list[RerankedResult] = []


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    words_a = set(tokenize(text_a))
    words_b = set(tokenize(text_b))
    if not words_a or not words_b:
        return 0.0
    intersection = len(words_a & words_b)
    union = len(words_a | words_b)
    return intersection / union


def compress_context(
    results: list[RerankedResult],
    max_context_chars: int | None = None,
    similarity_threshold: float | None = None,
) -> CompressionResult:
    """Deduplicate near-identical chunks, then enforce a total character budget.

    `results` must already be sorted best-first (as `RerankerModel.rerank`
    returns them) — both passes are rank-order-sensitive: deduplication
    always keeps the higher-ranked chunk of a redundant pair, and budget
    enforcement drops from the bottom of the (deduplicated) ranking first.
    """
    max_context_chars = max_context_chars if max_context_chars is not None else settings.max_context_chars
    similarity_threshold = (
        similarity_threshold if similarity_threshold is not None else settings.context_similarity_threshold
    )

    kept: list[RerankedResult] = []
    dropped_duplicate: list[RerankedResult] = []

    for candidate in results:
        is_duplicate = any(_jaccard_similarity(candidate.text, k.text) >= similarity_threshold for k in kept)
        if is_duplicate:
            dropped_duplicate.append(candidate)
        else:
            kept.append(candidate)

    budget_kept: list[RerankedResult] = []
    dropped_budget: list[RerankedResult] = []
    running_total = 0
    for candidate in kept:
        candidate_len = len(candidate.text)
        if running_total + candidate_len > max_context_chars and budget_kept:
            # Always keep at least one chunk even if it alone exceeds the
            # budget - some context beats none, and RERANK_TOP_K/CHUNK_SIZE
            # defaults make a single chunk exceeding the budget unlikely.
            dropped_budget.append(candidate)
            continue
        budget_kept.append(candidate)
        running_total += candidate_len

    logger.info(
        "Context compression: kept=%d dropped_duplicate=%d dropped_budget=%d total_chars=%d",
        len(budget_kept),
        len(dropped_duplicate),
        len(dropped_budget),
        running_total,
    )

    return CompressionResult(
        kept=budget_kept, dropped_duplicate=dropped_duplicate, dropped_budget=dropped_budget
    )
