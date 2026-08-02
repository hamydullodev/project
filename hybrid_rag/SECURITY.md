# Security Policy

## Scope

UzLaw AI is a local-first application: no accounts, no hosted multi-user
deployment, no data leaves your machine after setup. The realistic
security surface is:

- The FastAPI backend (`api/`) and its input handling (`AskRequest`)
- The Next.js frontend's handling of untrusted content (retrieved chunk
  text, LLM output) when rendered as Markdown
- Dependency vulnerabilities in `requirements.txt` / `frontend/package.json`

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a security
vulnerability. Instead, email **abduroshyd@gmail.com** with:

- A description of the issue and its potential impact
- Steps to reproduce (a minimal example if possible)
- Any suggested fix, if you have one

You should expect an initial response within a few days. This is a
personal/educational project maintained outside of full-time work, so
please be patient — genuine reports are taken seriously regardless of
response time.

## Supported versions

Only the latest commit on `main` is supported. There are no maintained
release branches at this time.
