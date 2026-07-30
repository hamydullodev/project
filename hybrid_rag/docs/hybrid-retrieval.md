# Hybrid Retrieval

<sub>[← Back to README](../README.md)</sub>

## Chunking: one article = one chunk

`app/ingestion/chunker.py` prefers legal-structure-aware splitting (one
article — "N-modda" — becomes one semantic chunk) over blind
character-count splitting, falling back to the latter only when a
document doesn't look like a structured legal code (e.g. a generic
upload with no article markers). Any article whose body still exceeds
`CHUNK_SIZE` is further split with a recursive character splitter
(configurable overlap via `CHUNK_OVERLAP`), and every sub-chunk keeps the
parent article's full metadata — law name, article number, section, page
number — so a citation is never ambiguous about which article it came
from.

## Dense retrieval — FAISS

Each chunk is embedded with a multilingual sentence-transformers model
(`EMBEDDING_MODEL`) and indexed in FAISS. A query is embedded the same
way and compared by cosine similarity. Dense retrieval is good at
matching *meaning* — a paraphrased question still finds the right
article even when its wording differs from the source text.

## Sparse retrieval — BM25

BM25 indexes the same chunks by exact term statistics. It's good at
matching *exact legal terms and article numbers*, which dense embeddings
can blur (a `bge`/MiniLM embedding doesn't reliably distinguish
"56-modda" from "58-modda" — BM25 does).

> [!NOTE]
> BM25's raw score is an **unbounded** relevance score, not a probability
> — it can be single digits or several hundred depending on term
> rarity. The API also exposes a min-max **normalized** `[0, 1]` variant
> of both dense and sparse scores (`dense_score_normalized` /
> `sparse_score_normalized`) specifically so a frontend can render them
> as a percentage without producing nonsense like "3802%".

## Fusion

```
combined_score = DENSE_WEIGHT * dense_score_normalized
               + SPARSE_WEIGHT * sparse_score_normalized
```

Both inputs are min-max normalized *within the current candidate set*
before fusion, so the two engines' very different score scales (cosine
similarity vs. BM25) don't let one dominate the other by scale alone.
`TOP_K` candidates from each engine are unioned, fused, and sorted by
`combined_score`.

## Reranking — cross-encoder

The fused candidates go through a cross-encoder (`RERANKER_MODEL`), which
scores the *actual query-chunk pair* jointly (unlike dense/sparse
retrieval, which score the query and chunk independently) — a second,
more accurate pass over a much smaller candidate set. Its raw output is
mapped through a sigmoid to a genuine `[0, 1]` relevance probability
(`reranker_score`) — this is the score the product surfaces as a
bucketed "confidence" label (High ≥ 0.75, Medium ≥ 0.5, Low otherwise)
rather than a raw, overclaiming percentage.

## Context compression

Before prompting the LLM, near-duplicate chunks are dropped and the
remaining context is capped at `MAX_CONTEXT_CHARS` — keeping the prompt
focused on the highest-signal, non-redundant sources rather than padding
it with repetition.

## Known limitation: Uzbek morphology

BM25 does no stemming, and the default lightweight embedding model's
semantic similarity can also miss a query that uses a different
grammatical case of a key word than the source text. This is a
documented, real limitation of the lightweight default models on
Uzbek's rich morphology (see `tests/evaluation/golden_dataset.py`'s
comments for a concrete example that failed for exactly this reason) —
not a bug in the retrieval logic itself. A larger embedding model
(`BAAI/bge-m3`, `intfloat/multilingual-e5-large`) mitigates it at the
cost of RAM — see [`configuration.md`](configuration.md).
