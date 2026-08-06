import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

from app.config import REQUEST_TIMEOUT, USER_AGENT

SEARCH_URL = "https://duckduckgo.com/html/"
HEADERS = {"User-Agent": USER_AGENT}


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Run a general web search and return title/url/snippet results."""
    try:
        resp = requests.post(SEARCH_URL, data={"q": query}, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    for result in soup.select(".result")[:max_results]:
        link = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if not link:
            continue
        results.append(
            {
                "title": link.get_text(strip=True),
                "url": link.get("href", ""),
                "snippet": snippet.get_text(strip=True) if snippet else "",
            }
        )
    return results


@tool
def web_search_tool(query: str) -> list[dict]:
    """Search the public web for general, non-medical background info that the
    connected pharmacy sites (OXYmed, PharmaClick, Europharm) don't provide —
    e.g. a manufacturer's country of origin, an unfamiliar brand name, or
    where else in Uzbekistan a product might be sold. Returns a list of
    {title, url, snippet}. Never use this to answer medical, diagnosis, or
    treatment questions — those must always be declined and redirected to a
    qualified healthcare professional.
    """
    return web_search(query)
