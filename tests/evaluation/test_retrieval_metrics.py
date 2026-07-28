"""
Unit tests for the pure metric functions in app.rag.evaluation (Milestone 20).

These tests use small, hand-computed synthetic relevance lists — no
retriever, no embedding model, no real corpus — because the metric
formulas themselves (precision/recall/MRR/nDCG) are pure functions of a
list of booleans and should be verified in complete isolation from
whether retrieval itself works. `test_retrieval_evaluation.py` (same
directory) is where these functions get exercised against the real
pipeline and real corpus.
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import ndcg_score

from app.rag.evaluation import (
    _dcg_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


class TestPrecisionAtK:
    def test_all_relevant(self):
        assert precision_at_k([True, True, True], k=3) == 1.0

    def test_none_relevant(self):
        assert precision_at_k([False, False, False], k=3) == 0.0

    def test_mixed(self):
        # 2 of the top 3 are relevant.
        assert precision_at_k([True, False, True, False, False], k=3) == pytest.approx(2 / 3)

    def test_k_larger_than_list_uses_available_results_only(self):
        assert precision_at_k([True, False], k=10) == pytest.approx(0.5)

    def test_empty_results(self):
        assert precision_at_k([], k=5) == 0.0


class TestRecallAtK:
    def test_finds_all_relevant_within_k(self):
        assert recall_at_k([True, True, False], k=3, total_relevant=2) == 1.0

    def test_finds_some_relevant_within_k(self):
        # 1 of 2 total relevant items appears in the top 1.
        assert recall_at_k([True, False, True], k=1, total_relevant=2) == pytest.approx(0.5)

    def test_zero_total_relevant_is_zero_not_a_crash(self):
        assert recall_at_k([False, False], k=2, total_relevant=0) == 0.0

    def test_none_found(self):
        assert recall_at_k([False, False, False], k=3, total_relevant=1) == 0.0


class TestReciprocalRank:
    def test_first_result_relevant(self):
        assert reciprocal_rank([True, False, False]) == 1.0

    def test_third_result_relevant(self):
        assert reciprocal_rank([False, False, True]) == pytest.approx(1 / 3)

    def test_nothing_relevant(self):
        assert reciprocal_rank([False, False, False]) == 0.0

    def test_empty_list(self):
        assert reciprocal_rank([]) == 0.0


class TestNdcgAtK:
    def test_perfect_ordering_scores_one(self):
        # All 3 relevant items ranked first, out of exactly 3 relevant total.
        assert ndcg_at_k([True, True, True, False, False], k=5, total_relevant=3) == pytest.approx(1.0)

    def test_nothing_relevant_scores_zero(self):
        assert ndcg_at_k([False, False, False], k=3, total_relevant=0) == 0.0

    def test_worse_ordering_scores_less_than_perfect_ordering(self):
        # Same relevant count (2), but found later in the ranking - should score lower.
        perfect = ndcg_at_k([True, True, False, False], k=4, total_relevant=2)
        worse = ndcg_at_k([False, False, True, True], k=4, total_relevant=2)
        assert worse < perfect
        assert perfect == pytest.approx(1.0)

    @pytest.mark.parametrize(
        "flags,k,total_relevant",
        [
            ([True, False, True, False, True], 5, 3),
            ([False, True, False, False, True], 5, 2),
            ([True, True, True, True, True], 3, 5),
            ([False, False, False, True, False], 5, 1),
        ],
    )
    def test_matches_sklearn_ndcg_score(self, flags: list[bool], k: int, total_relevant: int):
        """Cross-check the hand-rolled formula against scikit-learn's reference implementation.

        sklearn's `ndcg_score(y_true, y_score, k=k)` ranks by `y_score`,
        so passing a strictly descending `y_score` (matching the given
        `flags` order) makes sklearn rank identically to our
        already-ranked `flags` list — for these to be numerically
        equivalent, every relevant item counted in `total_relevant` must
        already be present in `flags` (sklearn infers "ideal" purely from
        `y_true`'s own 1s, with no separate "some relevant items were
        never retrieved at all" concept) - true for every case above.
        """
        assert total_relevant == sum(flags), "fixture must include every relevant item for a fair sklearn comparison"

        y_true = np.array([[1 if f else 0 for f in flags]])
        y_score = np.array([[len(flags) - i for i in range(len(flags))]])  # strictly descending

        expected = ndcg_score(y_true, y_score, k=k)
        actual = ndcg_at_k(flags, k=k, total_relevant=total_relevant)
        assert actual == pytest.approx(expected, abs=1e-9)


class TestDcgAtKHelper:
    def test_earlier_rank_contributes_more_than_later_rank(self):
        # A single relevant item at rank 1 has higher DCG than the same
        # single item at rank 2, per the log2(rank + 1) discount.
        assert _dcg_at_k([True, False], k=2) > _dcg_at_k([False, True], k=2)
