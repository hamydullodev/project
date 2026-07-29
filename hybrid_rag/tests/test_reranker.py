"""
Unit tests for app.reranker.cross_encoder.

Loads the real, configured reranker model once (module-scoped fixture)
rather than mocking it — cross-encoder correctness (does a relevant pair
actually score higher than an irrelevant one) is exactly the behavior
worth verifying for real, and the default model is small enough to load
quickly. Uses the default device resolution (RERANKER_DEVICE=auto in
settings), which is the proven-working configuration on this project's
dev machine — see cross_encoder.py's module docstring for why forcing
device="cpu" specifically crashed during development.
"""

from __future__ import annotations

import pytest

from app.database.models import ChunkRecord
from app.reranker.cross_encoder import RerankedResult, RerankerModel
from app.retriever.hybrid_retriever import HybridSearchResult


@pytest.fixture(scope="module")
def reranker() -> RerankerModel:
    return RerankerModel()


def _result(chunk_id: str, **kwargs) -> HybridSearchResult:
    return HybridSearchResult(chunk_id=chunk_id, **kwargs)


def _chunk(chunk_id: str, text: str, **kwargs) -> ChunkRecord:
    defaults = dict(id=chunk_id, document_id="doc-1", chunk_index=0, char_count=len(text))
    defaults.update(kwargs)
    return ChunkRecord(text=text, **defaults)


def test_relevant_text_scores_higher_than_irrelevant(reranker: RerankerModel):
    candidates = [
        _result("relevant", combined_score=0.5),
        _result("irrelevant", combined_score=0.5),
    ]
    chunks = {
        "relevant": _chunk(
            "relevant",
            "155-modda. Mehnat shartnomasini bekor qilish tushunchasi va asoslari. "
            "Mehnat shartnomasi taraflardan birining tashabbusi bilan bekor qilinishi mumkin.",
        ),
        "irrelevant": _chunk(
            "irrelevant", "Butunlay aloqasiz mavzu: pomidor yetishtirish texnologiyasi haqida."
        ),
    }

    results = reranker.rerank(
        "Mehnat shartnomasini qanday bekor qilish mumkin?", candidates, chunks, top_k=2
    )

    assert results[0].chunk_id == "relevant"
    assert results[0].reranker_score > results[1].reranker_score


def test_scores_are_in_zero_one_range(reranker: RerankerModel):
    candidates = [_result("a"), _result("b")]
    chunks = {
        "a": _chunk("a", "Fuqarolik huquqi toʻgʻrisida."),
        "b": _chunk("b", "Boshqa mavzu haqida."),
    }

    results = reranker.rerank("Fuqarolik huquqi nima?", candidates, chunks, top_k=2)
    for r in results:
        assert 0.0 <= r.reranker_score <= 1.0


def test_results_sorted_descending(reranker: RerankerModel):
    candidates = [_result(f"c{i}") for i in range(4)]
    texts = {
        "c0": "Jinoyat kodeksi jazo choralari haqida.",
        "c1": "Mehnat shartnomasi tuzish tartibi.",
        "c2": "Fuqarolik huquqi va majburiyatlar.",
        "c3": "Iqtisodiy sud ishlarini yuritish.",
    }
    chunks = {cid: _chunk(cid, text) for cid, text in texts.items()}

    results = reranker.rerank("Jinoyat javobgarligi qanday belgilanadi?", candidates, chunks, top_k=4)
    scores = [r.reranker_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_top_k_limits_results(reranker: RerankerModel):
    candidates = [_result(f"c{i}") for i in range(5)]
    chunks = {f"c{i}": _chunk(f"c{i}", f"Matn raqami {i} haqida.") for i in range(5)}

    results = reranker.rerank("test", candidates, chunks, top_k=2)
    assert len(results) == 2


def test_empty_candidates_returns_empty_list(reranker: RerankerModel):
    assert reranker.rerank("test", [], {}, top_k=5) == []


def test_missing_chunk_data_is_skipped_gracefully(reranker: RerankerModel):
    candidates = [_result("has_data"), _result("missing_data")]
    chunks = {"has_data": _chunk("has_data", "Fuqarolik huquqi haqida matn.")}

    results = reranker.rerank("test", candidates, chunks, top_k=5)
    result_ids = {r.chunk_id for r in results}
    assert "missing_data" not in result_ids
    assert "has_data" in result_ids


def test_all_candidates_missing_data_returns_empty(reranker: RerankerModel):
    candidates = [_result("a"), _result("b")]
    assert reranker.rerank("test", candidates, {}, top_k=5) == []


def test_reranked_result_preserves_upstream_hybrid_scores(reranker: RerankerModel):
    candidates = [
        _result(
            "c1",
            dense_score=0.8,
            sparse_score=12.5,
            dense_score_normalized=0.9,
            sparse_score_normalized=0.7,
            combined_score=0.8,
        )
    ]
    chunks = {"c1": _chunk("c1", "Fuqarolik huquqi toʻgʻrisida.")}

    results = reranker.rerank("test", candidates, chunks, top_k=1)
    r = results[0]
    assert isinstance(r, RerankedResult)
    assert r.dense_score == 0.8
    assert r.sparse_score == 12.5
    assert r.dense_score_normalized == 0.9
    assert r.sparse_score_normalized == 0.7
    assert r.combined_score == 0.8
    assert r.text == "Fuqarolik huquqi toʻgʻrisida."


def test_reranked_result_carries_citation_metadata(reranker: RerankerModel):
    candidates = [_result("c1")]
    chunks = {
        "c1": _chunk(
            "c1",
            "Mehnat shartnomasi bekor qilinadi.",
            law_name="Mehnat kodeksi",
            article_number="155",
            section="1-BOB",
            page_number=3,
        )
    }

    results = reranker.rerank("test", candidates, chunks, top_k=1)
    r = results[0]
    assert r.law_name == "Mehnat kodeksi"
    assert r.article_number == "155"
    assert r.section == "1-BOB"
    assert r.page_number == 3


def test_default_top_k_comes_from_settings(reranker: RerankerModel):
    from app.config import settings

    n = settings.rerank_top_k + 3
    candidates = [_result(f"c{i}") for i in range(n)]
    chunks = {f"c{i}": _chunk(f"c{i}", f"Matn {i}.") for i in range(n)}

    results = reranker.rerank("test", candidates, chunks)  # no top_k passed
    assert len(results) == settings.rerank_top_k
