# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Repository polish: professional README, `docs/` folder, `LICENSE`,
  `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, ruff lint/format
  config.

## [0.3.0] — Design system unification

### Changed

- Full UI rebuild on the same design system as the sibling **Avia AI**
  project: shared color tokens (`app/ui/theme.py`), CSS (`app/ui/styles.py`),
  and component architecture (`app/ui/components/`), so both products read
  as one company's tools.
- Replaced the single-file Streamlit script with a proper multi-page app
  (`st.navigation`): Home, Medicine Search, Compare Prices, Nearby
  Pharmacies, Saved Medicines, History, Settings.
- Chat redesigned ChatGPT-style: blue user bubbles, borderless assistant
  text, word-by-word reveal animation, medicine result cards rendered
  inline per turn.

### Added

- `web_search_tool`: a DuckDuckGo-backed fallback for non-price background
  info (e.g. manufacturer country), explicitly barred from ever supplying
  price or availability data.
- Cheapest / best-value badges, the latter computed from real
  price-per-package-unit rather than a placeholder heuristic.
- Cropped, transparent-background logo mark used as the app's circular
  brand badge and favicon.

## [0.2.0] — Price comparison & assistant features

### Added

- `compare_products_tool` and `find_cheapest_tool` for side-by-side
  comparison and cheapest-variant lookup.
- `filter_products_tool` for natural-language price/brand/availability
  filtering.
- Favorites and search-history storage (SQLite).
- Streamlit UI: sidebar quick search, filters, recent searches, favorites.

## [0.1.0] — Initial build

### Added

- LangGraph agent (`app/agent/graph.py`) wired to a local Ollama model
  with forced tool-calling on the first step of every turn.
- Live scrapers for three Uzbekistan online pharmacies — OXYmed,
  PharmaClick, Europharm (`app/tools/scrapers/`).
- `search_products_tool` and `product_details_tool`.
- Grounding safeguard: the final answer is rebuilt deterministically from
  a product-lookup tool's raw JSON, never trusted verbatim from the LLM's
  free text.
- FastAPI backend (`main.py`) exposing `/chat`, `/recent-searches`,
  `/favorites`, `/price-alerts`, `/health`.
