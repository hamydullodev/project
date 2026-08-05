# Contributing to Avia AI

Thanks for considering a contribution! This is a small project, so the
process is intentionally lightweight.

## Getting set up

```bash
git clone https://github.com/<your-username>/avia-ai.git
cd avia-ai
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama pull llama3.2:3b
pytest -q
```

See the main [README](README.md) for full setup details.

## Workflow

1. Open an issue first for anything non-trivial, so we can agree on the
   approach before you invest time in it.
2. Fork the repo and create a branch off `main`:
   `git checkout -b feat/short-description`.
3. Keep changes focused — one logical change per pull request.
4. Add or update tests for anything you change in `app/`.
5. Run `pytest -q` locally before opening the PR.
6. Open a PR using the template — link the issue it resolves.

## Code style

- Python 3.12+, type hints on public functions.
- Docstrings explain *why*, not *what* — the code should already say what
  it does.
- No cloud LLM calls in `app/agent` or `app/tools` — this project's whole
  point is a **local** model. New tools must go through `app/api` for any
  network I/O.
- Never let the LLM fabricate a fact a tool should supply. If you touch
  `app/agent/nodes.py`, re-read `tests/test_guardrail.py` first.

## Reporting bugs / requesting features

Use the issue templates — they ask for exactly what's needed to reproduce
or evaluate the request.

## Security issues

Please don't open a public issue for a security vulnerability — see
[SECURITY.md](SECURITY.md) instead.
