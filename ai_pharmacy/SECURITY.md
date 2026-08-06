# Security Policy

## Supported Versions

This is an actively developed personal/portfolio project on a single
`main` branch — only the latest commit is supported.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for a security
vulnerability. Instead, email **jumanovhamydullo@gmail.com** with:

- A description of the vulnerability and its potential impact
- Steps to reproduce it
- Any relevant logs or proof-of-concept code

You should receive an acknowledgment within a few days. Once a fix is
available, it will be released and the reporter credited (unless they
prefer to stay anonymous).

## Notes on this project's attack surface

- No API keys or secrets are required — the LLM runs locally via Ollama,
  and the only outbound calls are to the three connected pharmacy sites
  and a public web-search endpoint (DuckDuckGo), all read-only.
- Configuration lives in a local `.env` file (see `.env.example`) and is
  never committed or logged.
- There is no authentication layer; both the FastAPI backend and the
  Streamlit UI are intended for local/single-user use, not as a
  multi-tenant public deployment as-is.
- User-supplied product data (favorites, search history, price alerts) is
  stored in a local SQLite file, never transmitted anywhere beyond the
  local backend.
