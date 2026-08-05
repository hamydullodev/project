# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Local speech-to-text (`faster-whisper`) for the chat input's voice
  recorder, pinned to Uzbek (`WHISPER_LANGUAGE`) instead of relying on
  auto-detection.
- Repository polish: professional README, `docs/` folder, GitHub Actions
  CI, issue/PR templates, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, `Dockerfile`.

## [0.2.0] — Avia AI redesign

### Changed

- Full UI rebrand from "AI Travel Agent" to **Avia AI**: new light color
  system (no purple), minimal top bar (logo only), native
  `st.navigation`-based sidebar (Chat / Reys natijalari / Taqqoslash /
  Viza xizmati / Sozlamalar) replacing the old tab layout.
- Chat redesigned ChatGPT-style: borderless assistant messages, blue user
  bubbles, server-side Markdown→HTML rendering (fixes stray tags leaking
  into the UI), word-by-word reveal animation.
- Flight cards: sort/filter controls, expandable details, an honest
  external "View on Google Flights" link instead of a fake "Book" button
  (no booking backend exists).

### Added

- **Viza xizmati** page: nationality + destination → six live web-searched
  categories (requirements, documents, embassy, processing time/cost,
  passport & photo rules, application steps, advisories), each with a
  real source link.
- Native drag-and-drop file attachment and voice recording in the chat
  input (`st.chat_input(accept_file=True, accept_audio=True)`).
- `recommend_destination_guide` tool: real, sourced attraction/hotel
  suggestions for a destination.
- Anti-hallucination guard (`app/agent/nodes.py::_sanitize_final_answer`)
  and a source-attachment guard (`_append_sources`) that verify the LLM's
  final answer against the tool output it was supposedly built from.

## [0.1.0] — Initial build

### Added

- LangGraph agent (`app/agent/graph.py`) wired to a local Ollama model
  with tool calling.
- Flight Search, Flight Comparison, Airport Search, Currency Conversion,
  Flight Status, Destination Weather, and Web Search tools, each backed
  by a real external API client in `app/api/`.
- Multi-provider flight data layer (Amadeus, AviationStack) selected via
  `FLIGHT_DATA_PROVIDER`.
- Streamlit UI: sidebar, chat, flight cards, comparison table.
- Initial pytest suite covering validators, formatting, and provider
  parsing.
