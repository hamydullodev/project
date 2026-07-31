# Changelog

All notable changes to this project are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Governance docs: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`.
- Chat UI extras: like/dislike on responses, chat search/filter in sidebar history.

### Changed
- Full interface redesign: real multi-turn chat (`st.chat_message`/`st.chat_input`), light blue + white theme, sidebar with chat history, saved responses, dataset/adapter browsers, and a collapsible info panel with live config and per-response metadata.
- Demo Mode now returns genuinely informative canned answers instead of a meta "no GPU" placeholder.
- README rewritten short and recruiter-friendly: purpose, architecture diagram, tools, screenshots, quick start.

### Fixed
- Demo answer matching no longer mismatches "QLoRA" questions to the "LoRA" canned answer.

## [0.2.0] — Colab & tests

### Added
- `notebooks/colab_finetune.ipynb` — run the full pipeline on a free Colab GPU.
- `tests/` — pytest suite covering dataset cleaning/splitting/conversion, the Alpaca prompt template, and config validation.

## [0.1.0] — Initial release

### Added
- End-to-end pipeline: dataset conversion/cleaning/splitting, config-driven LoRA/QLoRA training via Unsloth, base-vs-fine-tuned evaluation, and a Streamlit app for chat, comparison, dataset upload, and training diagnostics.
