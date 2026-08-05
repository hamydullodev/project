"""Unit tests for app.rag.query_processing."""

from __future__ import annotations

import pytest

from app.config import settings
from app.rag.query_processing import EmptyQueryError, preprocess_query


def test_preprocess_query_normalizes_ascii_apostrophe():
    assert preprocess_query("ma'no nima?") == "maʼno nima?"


def test_preprocess_query_collapses_whitespace():
    result = preprocess_query("Fuqarolik    huquqi   nima?")
    assert "  " not in result


def test_preprocess_query_strips_leading_trailing_whitespace():
    assert preprocess_query("  Fuqarolik huquqi nima?  ") == "Fuqarolik huquqi nima?"


def test_preprocess_query_preserves_uzbek_digraph_letter():
    result = preprocess_query("Oʻzbekiston qonuni nima?")
    assert "Oʻzbekiston" in result


def test_preprocess_query_empty_raises():
    with pytest.raises(EmptyQueryError):
        preprocess_query("")


def test_preprocess_query_whitespace_only_raises():
    with pytest.raises(EmptyQueryError):
        preprocess_query("     \n\t  ")


def test_preprocess_query_truncates_overly_long_query():
    long_query = "fuqarolik huquqi " * 200  # comfortably over MAX_QUERY_LENGTH
    result = preprocess_query(long_query)
    assert len(result) <= settings.max_query_length


def test_preprocess_query_normal_length_untouched():
    query = "Fuqarolik shartnomasi qanday tuziladi?"
    assert preprocess_query(query) == query
