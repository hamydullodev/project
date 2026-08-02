# Contributing

Thanks for considering a contribution to UzLaw AI.

## Local setup

```bash
make setup-dev     # venv + Python deps + dev tooling + frontend deps
make api           # terminal 1 — FastAPI backend, :8000
make frontend      # terminal 2 — Next.js dev server, :3000
```

See the [README's Quick Start](README.md#-quick-start) for Ollama setup
and first-time indexing.

## Before opening a PR

```bash
make lint          # ruff + mypy + eslint
make format         # black + isort
make test           # full Python test suite
```

CI (`.github/workflows/ci.yml`) runs lint/type-check/build on every PR.
It deliberately does **not** run the full pytest suite — that needs a
running Ollama instance and a multi-GB embedding model download, which
would make CI slow and flaky. Run `make test` locally before opening a
PR that touches `app/` or `api/`.

## Code style

- Python: `black` + `isort` for formatting, `ruff` for linting, `mypy`
  for type-checking. Config lives in `pyproject.toml`.
- Frontend: `eslint` (config in `frontend/eslint.config.mjs`). Prettier
  is not configured separately — rely on your editor's formatter plus
  ESLint's own style rules.
- This codebase's docstring convention documents **why** a module/class
  exists and **how** it works internally, not just what it does — see
  any existing file in `app/` for the pattern. New non-trivial modules
  should follow it.

## Commit messages

Short, imperative, present tense ("add X", not "added X" or "adds X").
Explain *why* in the body when the reason isn't obvious from the diff
alone.

## Reporting bugs / requesting features

Use the issue templates under `.github/ISSUE_TEMPLATE/`. For retrieval-
quality issues specifically, include the exact query and, if possible,
which article you expected it to find — that's the fastest path to a
golden-dataset regression test (see
[`docs/evaluation.md`](docs/evaluation.md)).

## Security issues

Do not open a public issue — see [`SECURITY.md`](SECURITY.md).
