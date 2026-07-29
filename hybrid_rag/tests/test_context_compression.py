"""Unit tests for app.rag.context_compression."""

from __future__ import annotations

from app.rag.context_compression import _jaccard_similarity, compress_context
from app.reranker.cross_encoder import RerankedResult


def _result(chunk_id: str, text: str, reranker_score: float) -> RerankedResult:
    return RerankedResult(chunk_id=chunk_id, text=text, reranker_score=reranker_score)


# ---------------------------------------------------------------------------
# _jaccard_similarity
# ---------------------------------------------------------------------------


def test_jaccard_identical_text_is_one():
    text = "fuqarolik huquqi toʻgʻrisida qoida"
    assert _jaccard_similarity(text, text) == 1.0


def test_jaccard_completely_different_text_is_zero():
    a = "fuqarolik huquqi toʻgʻrisida"
    b = "pomidor yetishtirish texnologiyasi"
    assert _jaccard_similarity(a, b) == 0.0


def test_jaccard_partial_overlap_between_zero_and_one():
    a = "fuqarolik huquqi va majburiyat toʻgʻrisida"
    b = "fuqarolik huquqi va mulk masalasi"
    sim = _jaccard_similarity(a, b)
    assert 0.0 < sim < 1.0


def test_jaccard_empty_text_is_zero():
    assert _jaccard_similarity("", "fuqarolik huquqi") == 0.0
    assert _jaccard_similarity("fuqarolik huquqi", "") == 0.0


# ---------------------------------------------------------------------------
# compress_context — deduplication
# ---------------------------------------------------------------------------


def test_compress_context_empty_list():
    result = compress_context([])
    assert result.kept == []
    assert result.dropped_duplicate == []
    assert result.dropped_budget == []


def test_compress_context_no_duplicates_all_kept():
    results = [
        _result("c1", "155-modda. Mehnat shartnomasini bekor qilish tushunchasi.", 0.9),
        _result("c2", "Jinoyat sodir etgan shaxs jazoga tortiladi.", 0.8),
        _result("c3", "Fuqarolik shartnomasi ikki taraf oʻrtasida tuziladi.", 0.7),
    ]
    result = compress_context(results, max_context_chars=10000)
    assert len(result.kept) == 3
    assert result.dropped_duplicate == []


def test_compress_context_removes_overlapping_duplicate():
    # Simulates two adjacent overlapping sub-chunks of the same article.
    shared = "155-modda. Mehnat shartnomasini bekor qilish tushunchasi va asoslari juda muhim mavzu"
    results = [
        _result("c1", shared + " birinchi qism davomi.", 0.9),
        _result("c2", shared + " ikkinchi qism davomi.", 0.85),
    ]
    result = compress_context(results, max_context_chars=10000, similarity_threshold=0.6)
    assert len(result.kept) == 1
    assert result.kept[0].chunk_id == "c1"  # higher-ranked one survives
    assert len(result.dropped_duplicate) == 1
    assert result.dropped_duplicate[0].chunk_id == "c2"


def test_compress_context_keeps_higher_ranked_of_duplicate_pair():
    shared_text = "Bir xil matn butunlay qaytarilgan holatda"
    results = [
        _result("best", shared_text, 0.95),
        _result("worse", shared_text, 0.5),
    ]
    result = compress_context(results, max_context_chars=10000)
    assert [r.chunk_id for r in result.kept] == ["best"]


def test_compress_context_custom_similarity_threshold_stricter():
    a = "fuqarolik huquqi va majburiyat toʻgʻrisida qisqa matn"
    b = "fuqarolik huquqi va mulk masalasi haqida boshqa matn"
    results = [_result("c1", a, 0.9), _result("c2", b, 0.8)]

    # With a very low threshold, even modest overlap counts as duplicate.
    strict_result = compress_context(results, max_context_chars=10000, similarity_threshold=0.1)
    assert len(strict_result.kept) == 1

    # With a very high threshold, only near-identical text is duplicate.
    lenient_result = compress_context(results, max_context_chars=10000, similarity_threshold=0.99)
    assert len(lenient_result.kept) == 2


# ---------------------------------------------------------------------------
# compress_context — budget enforcement
# ---------------------------------------------------------------------------


def test_compress_context_enforces_character_budget():
    results = [
        _result("c1", "a" * 100, 0.9),
        _result("c2", "b" * 100, 0.8),
        _result("c3", "c" * 100, 0.7),
    ]
    result = compress_context(results, max_context_chars=150)
    assert len(result.kept) == 1  # only c1 fits (100 <= 150, but +100 more would exceed)
    assert result.kept[0].chunk_id == "c1"
    assert len(result.dropped_budget) == 2


def test_compress_context_always_keeps_at_least_one_chunk():
    results = [_result("c1", "x" * 500, 0.9)]
    result = compress_context(results, max_context_chars=10)  # budget smaller than the chunk itself
    assert len(result.kept) == 1
    assert result.dropped_budget == []


def test_compress_context_budget_drops_lowest_ranked_first():
    results = [
        _result("c1", "a" * 50, 0.9),
        _result("c2", "b" * 50, 0.8),
        _result("c3", "c" * 50, 0.7),
    ]
    result = compress_context(results, max_context_chars=110)
    kept_ids = [r.chunk_id for r in result.kept]
    assert kept_ids == ["c1", "c2"]  # c3 (lowest ranked) dropped for budget
    assert result.dropped_budget[0].chunk_id == "c3"


def test_compress_context_result_accounts_for_every_input():
    results = [
        _result("c1", "a" * 50, 0.9),
        _result("c2", "a" * 50, 0.85),  # duplicate of c1
        _result("c3", "c" * 5000, 0.7),  # unique but blows the budget
    ]
    result = compress_context(results, max_context_chars=100, similarity_threshold=0.6)
    total_accounted = len(result.kept) + len(result.dropped_duplicate) + len(result.dropped_budget)
    assert total_accounted == len(results)
