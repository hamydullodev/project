"""
Unit tests for app.retriever.tokenizer and app.retriever.bm25_index.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.retriever.bm25_index import BM25IndexError, BM25SparseIndex
from app.retriever.tokenizer import tokenize

# ---------------------------------------------------------------------------
# tokenizer.py
# ---------------------------------------------------------------------------


def test_tokenize_keeps_uzbek_digraph_letter_attached():
    assert tokenize("Oʻzbekiston") == ["oʻzbekiston"]


def test_tokenize_keeps_uzbek_glottal_stop_letter_attached():
    assert tokenize("maʼno eʼtirof") == ["maʼno", "eʼtirof"]


def test_tokenize_lowercases():
    assert tokenize("FUQAROLIK Kodeksi") == ["fuqarolik", "kodeksi"]


def test_tokenize_splits_on_punctuation_and_hyphens():
    assert tokenize("1-modda. Fuqarolik qonunchiligi.") == [
        "1",
        "modda",
        "fuqarolik",
        "qonunchiligi",
    ]


def test_tokenize_empty_string():
    assert tokenize("") == []


def test_tokenize_whitespace_only():
    assert tokenize("   \n\t  ") == []


# ---------------------------------------------------------------------------
# bm25_index.py
# ---------------------------------------------------------------------------

CORPUS_IDS = ["c1", "c2", "c3"]
CORPUS_TEXTS = [
    "1-modda. Fuqarolik qonunchiligi fuqarolik huquqlarini tartibga soladi.",
    "2-modda. Mehnat shartnomasi ish beruvchi va xodim oʻrtasida tuziladi.",
    "3-modda. Jinoyat sodir etgan shaxs jazoga tortiladi.",
]


@pytest.fixture()
def index() -> BM25SparseIndex:
    idx = BM25SparseIndex()
    idx.build(CORPUS_IDS, CORPUS_TEXTS)
    return idx


def test_new_index_is_empty():
    idx = BM25SparseIndex()
    assert idx.is_empty
    assert len(idx) == 0


def test_build_populates_index(index: BM25SparseIndex):
    assert len(index) == 3
    assert not index.is_empty


def test_build_mismatched_lengths_raises():
    idx = BM25SparseIndex()
    with pytest.raises(ValueError):
        idx.build(["a", "b"], ["only one text"])


def test_build_empty_corpus_gives_empty_index():
    idx = BM25SparseIndex()
    idx.build([], [])
    assert idx.is_empty
    assert idx.search("anything", top_k=5) == []


def test_search_finds_exact_term_match(index: BM25SparseIndex):
    results = index.search("fuqarolik", top_k=3)
    assert len(results) >= 1
    assert results[0][0] == "c1"
    assert results[0][1] > 0


def test_search_ranks_by_score_descending(index: BM25SparseIndex):
    results = index.search("mehnat shartnomasi", top_k=3)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_search_no_matching_terms_returns_empty(index: BM25SparseIndex):
    results = index.search("qalampir behavior xylophone", top_k=3)
    assert results == []


def test_search_on_empty_index_returns_empty():
    idx = BM25SparseIndex()
    assert idx.search("fuqarolik", top_k=5) == []


def test_search_empty_query_returns_empty(index: BM25SparseIndex):
    assert index.search("", top_k=5) == []
    assert index.search("!!! ...", top_k=5) == []


def test_search_respects_top_k(index: BM25SparseIndex):
    results = index.search("modda", top_k=2)
    assert len(results) <= 2


def test_article_number_is_matchable_as_a_token(index: BM25SparseIndex):
    """Article numbers should be tokenized separately from 'modda' so a
    query for a specific article number can match it lexically."""
    results = index.search("2", top_k=3)
    assert any(cid == "c2" for cid, _ in results)


# -- persistence ------------------------------------------------------------------


def test_save_and_load_round_trip(index: BM25SparseIndex, tmp_path: Path):
    path = tmp_path / "bm25.pkl"
    index.save(path)

    loaded = BM25SparseIndex.load(path)
    assert len(loaded) == len(index)

    original_results = index.search("mehnat shartnomasi", top_k=3)
    loaded_results = loaded.search("mehnat shartnomasi", top_k=3)
    assert original_results == loaded_results


def test_save_creates_single_file(index: BM25SparseIndex, tmp_path: Path):
    path = tmp_path / "bm25_index.pkl"
    index.save(path)
    assert path.exists()


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(BM25IndexError):
        BM25SparseIndex.load(tmp_path / "does_not_exist.pkl")


def test_load_corrupted_file_raises(tmp_path: Path):
    path = tmp_path / "corrupted.pkl"
    path.write_bytes(b"this is not a valid pickle file at all")

    with pytest.raises(BM25IndexError):
        BM25SparseIndex.load(path)


def test_load_unexpected_format_raises(tmp_path: Path):
    import pickle

    path = tmp_path / "wrong_format.pkl"
    with path.open("wb") as f:
        pickle.dump({"unexpected": "structure"}, f)

    with pytest.raises(BM25IndexError):
        BM25SparseIndex.load(path)


def test_rebuild_replaces_entire_corpus(index: BM25SparseIndex):
    """BM25 has no incremental add — build() always fully replaces the
    corpus, unlike FAISSVectorStore.add(). Uses a 3-document replacement
    corpus (not 1 or 2): with too few documents, a term appearing in
    exactly half of them gets a BM25 IDF of exactly zero by design (the
    classic Robertson/Sparck-Jones IDF formula), which would make this
    test's assertion depend on that degenerate arithmetic rather than on
    the behavior actually being tested (that rebuilding replaces the
    corpus).
    """
    new_ids = ["d1", "d2", "d3"]
    new_texts = [
        "Butunlay yangi hujjat matni.",
        "Boshqa mutlaqo aloqasiz mavzu.",
        "Yana bir aloqasiz gap.",
    ]
    index.build(new_ids, new_texts)

    assert len(index) == 3
    assert index.search("fuqarolik", top_k=5) == []  # old corpus is gone
    assert index.search("hujjat", top_k=5)[0][0] == "d1"
