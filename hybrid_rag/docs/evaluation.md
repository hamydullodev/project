# Evaluation

<sub>[← Back to README](../README.md)</sub>

## Retrieval metrics

`app/rag/evaluation.py` implements four standard information-retrieval
metrics, hand-implemented (cross-checked against scikit-learn's
reference `ndcg_score` in `test_retrieval_metrics.py` rather than
delegated to a library):

| Metric | What it measures |
|---|---|
| **Precision@K** | Of the top K retrieved chunks, what fraction are actually relevant? |
| **Recall@K** | Of all relevant chunks, what fraction appear in the top K? |
| **MRR** | Mean Reciprocal Rank — how high up the *first* relevant result lands, averaged over queries |
| **nDCG@K** | Normalized Discounted Cumulative Gain — rewards relevant results appearing *earlier*, not just present |

Relevance is graded at the **article level**, not the chunk level — a
retrieved chunk counts as relevant if it belongs to the article the
golden query is actually about, since that's the unit a user cites and
verifies against, not an arbitrary sub-chunk boundary.

## The golden dataset

`tests/evaluation/golden_dataset.py` holds 8 hand-verified
(query → relevant article) pairs, at least one per legal code, each
built by finding a distinctive fact in the real source text and phrasing
a natural Uzbek question about it — not synthetically generated. Current
results against the indexed corpus:

| Metric | Score |
|---|---|
| Precision@5 | 0.20 *(ceiling for this dataset — exactly 1 relevant article per query, in 5 slots)* |
| Recall@5 | 1.00 |
| MRR | 0.70 |
| nDCG@5 | 0.77 |

`test_retrieval_evaluation.py` asserts these stay above a floor — not a
perfect score, deliberately loose for an 8-query sample — as a
regression guard: a future change to chunking, the embedding model, or
fusion weights that meaningfully drops retrieval quality fails this test.

## Testing philosophy

The suite favors real components over mocks wherever the real component
is fast and deterministic enough to use directly — the actual chunker,
the actual SQLite repository, the actual FAISS/BM25 indexes over small
in-memory corpora. Mocks are reserved for genuinely external, slow, or
non-deterministic dependencies (Ollama's HTTP calls).

A handful of tests deliberately run against this project's own real,
already-indexed corpus rather than an isolated fixture — representative
behavior, not test pollution, since retrieval quality against synthetic
fixtures wouldn't say anything meaningful about real-world quality.
These specific tests need the real corpus indexed first, and (for
generation-dependent tests) a running `ollama serve` with `LLM_MODEL`
pulled.

```bash
python -m pytest                        # full suite
python -m pytest -k "not page"           # skip the slower Streamlit AppTest suites
python -m pytest tests/evaluation/ -v    # retrieval-quality metrics only
```

## A note on small local LLMs

The default `LLM_MODEL`, `llama3.2:3b`, is small (3B parameters) and can
occasionally produce repetitive or self-contradictory answers under a
sparse retrieved context (see `app/llm/ollama_client.py`'s docstring for
the full investigation). This is a model-capability limitation, not a
pipeline bug — a larger model (`qwen2.5:7b` or similar, RAM permitting)
is the direct fix if you see it in practice.
