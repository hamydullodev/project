"""
Unit tests for app.ingestion.legal_parser and app.ingestion.chunker.

Uses small synthetic legal-code-shaped text fixtures (mirroring the real
corpus's structure) rather than the full real files, so tests run fast and
pin down exact expected behavior instead of just "it didn't crash."
"""

from __future__ import annotations

from app.ingestion.chunker import (
    PageMapper,
    approximate_token_count,
    chunk_document,
)
from app.ingestion.legal_parser import (
    ParsedArticle,
    deduplicate_articles,
    parse_legal_structure,
    strip_legal_noise,
)
from app.ingestion.loaders import LoadedDocument

SAMPLE_LAW = """\
OʻZBEKISTON RESPUBLIKASINING FUQAROLIK KODEKSI
Birinchi qism
I BOʻLIM
UMUMIY QOIDALAR
1-Kichik boʻlim
ASOSIY QOIDALAR
Oldingi tahrirga qarang.
1-BOB.
FUQAROLIK QONUNCHILIGI
(1-bobning nomi Oʻzbekiston Respublikasining 2021-yil 21-apreldagi OʻRQ-683-sonli Qonuni tahririda — Qonunchilik maʼlumotlari milliy bazasi, 21.04.2021-y., 03/21/683/0375-son)
Oldingi tahrirga qarang.
1-modda. Fuqarolik qonunchiligining asosiy negizlari
Fuqarolik qonunchiligi ular tomonidan tartibga solinadigan munosabatlar ishtirokchilarining tengligini eʼtirof etishga asoslanadi.
(1-moddaning birinchi qismi Oʻzbekiston Respublikasining 2021-yil 21-apreldagi OʻRQ-683-sonli Qonuni tahririda — Qonunchilik maʼlumotlari milliy bazasi, 21.04.2021-y., 03/21/683/0375-son)

 LexUZ sharhi
Qarang: Oʻzbekiston Respublikasi Konstitutsiyasining 13-moddasi.
Fuqarolar oʻz fuqarolik huquqlariga oʻz erklariga muvofiq ega boʻladilar.
2-modda. Fuqarolik qonunchiligi bilan tartibga solinadigan munosabatlar
Fuqarolik qonunchiligi fuqarolik muomalasi ishtirokchilarining huquqiy holatini belgilaydi.
"""

NON_LEGAL_TEXT = """\
This is a generic uploaded document with no legal article structure at all.
It just has plain paragraphs of text that should be split by character count
instead of by article boundaries, since there is nothing resembling a
"N-modda." marker anywhere in this text for the parser to latch onto.
""" * 20


# ---------------------------------------------------------------------------
# legal_parser.py — noise stripping
# ---------------------------------------------------------------------------


def test_strip_legal_noise_removes_all_boilerplate():
    cleaned = strip_legal_noise(SAMPLE_LAW)
    assert "Oldingi tahrirga qarang." not in cleaned
    assert "tahririda" not in cleaned  # revision footnote parens removed
    assert "LexUZ sharhi" not in cleaned
    assert "Qarang: Oʻzbekiston Respublikasi Konstitutsiyasining" not in cleaned
    # Real content must survive.
    assert "Fuqarolik qonunchiligining asosiy negizlari" in cleaned
    assert "Fuqarolar oʻz fuqarolik huquqlariga" in cleaned


# ---------------------------------------------------------------------------
# legal_parser.py — structure parsing
# ---------------------------------------------------------------------------


def test_parse_legal_structure_finds_articles_with_breadcrumbs():
    cleaned = strip_legal_noise(SAMPLE_LAW)
    articles = parse_legal_structure(cleaned)

    assert len(articles) == 2
    assert articles[0].article_number == "1"
    assert articles[1].article_number == "2"
    assert "1-kichik boʻlim" in articles[0].section
    assert "1-bob" in articles[0].section
    assert "FUQAROLIK QONUNCHILIGI" in articles[0].section


def test_parse_legal_structure_article_text_includes_header_and_merges_split_body():
    cleaned = strip_legal_noise(SAMPLE_LAW)
    articles = parse_legal_structure(cleaned)

    # Article 1's body was interrupted by a LexUZ sharhi block in the
    # source; after noise stripping the two body sentences must be
    # contiguous in the article's text.
    assert articles[0].text.startswith("1-modda.")
    assert "tengligini eʼtirof etishga asoslanadi." in articles[0].text
    assert "Fuqarolar oʻz fuqarolik huquqlariga" in articles[0].text


def test_parse_legal_structure_returns_empty_for_non_legal_text():
    assert parse_legal_structure(NON_LEGAL_TEXT) == []


def test_parse_legal_structure_offsets_point_to_article_start():
    cleaned = strip_legal_noise(SAMPLE_LAW)
    articles = parse_legal_structure(cleaned)
    for article in articles:
        assert cleaned[article.start_offset : article.start_offset + 10] == article.text[:10]


# ---------------------------------------------------------------------------
# legal_parser.py — deduplication
# ---------------------------------------------------------------------------


def test_deduplicate_articles_drops_exact_repeats():
    articles = [
        ParsedArticle(article_number="1", section=None, text="1-modda. Same text."),
        ParsedArticle(article_number="2", section=None, text="2-modda. Other text."),
        ParsedArticle(article_number="1", section=None, text="1-modda. Same text."),  # exact repeat
    ]
    deduped = deduplicate_articles(articles)
    assert len(deduped) == 2
    assert [a.article_number for a in deduped] == ["1", "2"]


def test_deduplicate_articles_keeps_number_collisions_with_different_text():
    """Two genuinely different articles sharing a flattened number (e.g. a
    superscript-inserted article) must both survive — only identical
    (number, text) pairs are duplicates."""
    articles = [
        ParsedArticle(article_number="261", section=None, text="261-modda. Neustoyka shakllari"),
        ParsedArticle(
            article_number="261", section=None, text="261-modda. Toʻlovga qobiliyatsizlik"
        ),
    ]
    deduped = deduplicate_articles(articles)
    assert len(deduped) == 2


# ---------------------------------------------------------------------------
# chunker.py — approximate_token_count
# ---------------------------------------------------------------------------


def test_approximate_token_count_reasonable():
    text = "1-modda. Fuqarolik qonunchiligi."
    count = approximate_token_count(text)
    # "1", "-modda", ".", "Fuqarolik", "qonunchiligi", "." -> at least a
    # handful of tokens; the exact count depends on the regex, we just
    # assert it's in a sane ballpark, not zero and not len(text).
    assert 3 <= count <= len(text)


# ---------------------------------------------------------------------------
# chunker.py — PageMapper
# ---------------------------------------------------------------------------


def test_page_mapper_single_page_returns_none():
    mapper = PageMapper(["only one page of text"])
    assert mapper.page_for_offset(0) is None
    assert mapper.page_for_offset(5) is None


def test_page_mapper_multi_page_resolves_correct_page():
    pages = ["a" * 100, "b" * 100, "c" * 100]
    mapper = PageMapper(pages)
    assert mapper.page_for_offset(0) == 1
    assert mapper.page_for_offset(50) == 1
    # page 2 starts at offset 100 + 2 (separator) = 102
    assert mapper.page_for_offset(102) == 2
    assert mapper.page_for_offset(150) == 2
    assert mapper.page_for_offset(300) == 3


# ---------------------------------------------------------------------------
# chunker.py — chunk_document (end to end)
# ---------------------------------------------------------------------------


def _loaded(text: str) -> LoadedDocument:
    return LoadedDocument(file_path="test.txt", file_type="txt", pages=[text])


def test_chunk_document_legal_structure_path():
    doc = _loaded(SAMPLE_LAW)
    chunks = chunk_document(doc, file_name="fuqorolik.txt", chunk_size=800, chunk_overlap=100)

    assert len(chunks) == 2
    assert chunks[0].article_number == "1"
    assert chunks[0].law_name == "OʻZBEKISTON RESPUBLIKASINING FUQAROLIK KODEKSI"
    assert chunks[1].article_number == "2"
    # Single-page TXT input -> no page numbers.
    assert all(c.page_number is None for c in chunks)


def test_chunk_document_fallback_path_for_non_legal_text():
    doc = _loaded(NON_LEGAL_TEXT)
    chunks = chunk_document(doc, file_name="generic.txt", chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(c.article_number is None for c in chunks)
    assert all(c.section is None for c in chunks)
    assert all(c.char_count <= 200 for c in chunks)


def test_chunk_document_splits_long_article_and_preserves_metadata():
    long_body = "Uzun modda matni. " * 100  # comfortably over chunk_size
    text = f"TEST KODEKSI\n1-modda. Uzun modda\n{long_body}\n"
    doc = _loaded(text)

    chunks = chunk_document(doc, file_name="test.txt", chunk_size=300, chunk_overlap=50)

    assert len(chunks) > 1
    assert all(c.article_number == "1" for c in chunks)
    assert all(c.law_name == "TEST KODEKSI" for c in chunks)
    assert all(c.char_count <= 300 for c in chunks)
    # chunk_index must be sequential starting at 0.
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_document_short_article_is_single_chunk():
    text = "TEST KODEKSI\n1-modda. Qisqa modda\nQisqa matn.\n"
    doc = _loaded(text)

    chunks = chunk_document(doc, file_name="test.txt", chunk_size=800, chunk_overlap=100)

    assert len(chunks) == 1
    assert chunks[0].text.startswith("1-modda.")


def test_chunk_document_token_strategy_respects_token_budget():
    long_body = "soʻz " * 500
    text = f"TEST KODEKSI\n1-modda. Token test\n{long_body}\n"
    doc = _loaded(text)

    chunks = chunk_document(
        doc, file_name="test.txt", chunk_size=50, chunk_overlap=5, strategy="token"
    )

    assert len(chunks) > 1
    for c in chunks:
        assert approximate_token_count(c.text) <= 50
