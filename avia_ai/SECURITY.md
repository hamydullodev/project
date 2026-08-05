# Security Policy

## Supported Versions

This is an actively developed personal/portfolio project on a single
`main` branch — only the latest commit is supported.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for a security
vulnerability. Instead, email **abduroshyd@gmail.com** with:

- A description of the vulnerability and its potential impact
- Steps to reproduce it
- Any relevant logs or proof-of-concept code

You should receive an acknowledgment within a few days. Once a fix is
available, it will be released and the reporter credited (unless they
prefer to stay anonymous).

## Notes on this project's attack surface

- All external API keys are read from a local `.env` file (see
  `.env.example`) and are never committed or logged.
- This app makes outbound HTTP calls to third-party APIs (Amadeus,
  AviationStack, Geoapify, ExchangeRate-API, OpenWeatherMap, Serper) and
  runs a local LLM via Ollama — it does not expose any inbound network
  service beyond the Streamlit dev server itself.
- There is no authentication layer; this app is intended for local/
  single-user use, not as a multi-tenant public deployment as-is.
