# Development Guide

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama pull llama3.2:3b
```

## Running

```bash
ollama serve                 # terminal 1
streamlit run main.py        # terminal 2
pytest -q                    # tests
```

## Adding a new tool

1. Add the network client to `app/api/<provider>.py` (the only layer
   allowed to do HTTP I/O), with its own exception handling using the
   shared types in `app/api/exceptions.py`.
2. If it returns structured data, add a Pydantic model to
   `app/api/schemas.py`.
3. Add the `@tool`-decorated function in `app/tools/<name>.py`. Validate
   inputs (`app/utils/validators.py`), catch `ProviderError`, and return a
   plain formatted string — never let an exception escape.
4. Register it in `app/tools/__init__.py`'s `ALL_TOOLS` list.
5. If the tool sources facts from the web, make sure a real source link
   ends up in the response — `app/agent/nodes.py::_append_sources` only
   back-fills a link for tools listed in `_WEB_SOURCED_TOOLS`; add yours
   there if it uses `web_search`/Serper under the hood.
6. Write a test. If the tool touches money/dates/facts a small local
   model could plausibly hallucinate, add a guardrail test modeled on
   `tests/test_guardrail.py`.

## Adding a new flight data provider

1. Add `app/api/<provider>.py` exposing `search_flights(query:
   FlightSearchQuery) -> list[Flight]`.
2. Add the provider to `FlightDataProvider` in `app/config.py`.
3. Wire it into `app/api/provider.py::get_flight_provider_client`.
4. If the provider can't supply a price (like AviationStack), leave
   `Flight.price = None` — never default it to `0` or guess.

## Adding a new UI page

1. Create `app/ui/pages/<name>_page.py` with a `render()` function.
2. Register it as an `st.Page(...)` in `main.py`, with a unique
   `url_path` — `st.Page` infers the URL from the function name by
   default, and every page here is named `render`, so an explicit,
   distinct `url_path` is required or Streamlit will raise a
   `StreamlitAPIException` about duplicate pathnames.

## Testing

```bash
pytest -q
```

Tests are grouped by what they protect:

- `test_validators.py`, `test_formatter.py` — pure utility logic.
- `test_aviationstack.py`, `test_geoapify.py`, `test_serper.py` —
  provider response parsing, using static fixture dicts (no network
  calls in the test suite itself).
- `test_planner.py` — relative date resolution.
- `test_guardrail.py` — the anti-hallucination and source-attachment
  guards. **If you touch `app/agent/nodes.py`, run this file first.**

## Code style

- Type hints on public functions; `from __future__ import annotations` at
  the top of modules using modern union syntax.
- Docstrings explain *why* a non-obvious decision was made, not what the
  code visibly does.
- No comments restating the code.
