from app.api.schemas import WebSearchResult


def test_web_search_result_defaults_snippet_to_empty():
    result = WebSearchResult(title="Example", link="https://example.com")
    assert result.snippet == ""
