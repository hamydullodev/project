# Contributing to AI Pharmacy

Thanks for considering a contribution! This is a small project, so the
process is intentionally lightweight.

## Getting set up

```bash
git clone https://github.com/<your-username>/project.git
cd project/ai_pharmacy
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
ollama pull llama3.2:3b
```

See the main [README](README.md) for full setup details.

## Workflow

1. Open an issue first for anything non-trivial, so we can agree on the
   approach before you invest time in it.
2. Fork the repo and create a branch off `main`:
   `git checkout -b feat/short-description`.
3. Keep changes focused — one logical change per pull request.
4. Run `ruff format` and `ruff check` locally before opening the PR.
5. Open a PR — link the issue it resolves.

## Code style

- Python 3.12+, type hints on public functions.
- Docstrings explain *why*, not *what* — the code should already say what
  it does.
- No cloud LLM calls in `app/agent` or `app/tools` — this project's whole
  point is a **local** model via Ollama.
- Never let the LLM fabricate a fact a tool should supply. If you touch
  `app/agent/nodes.py` or `app/agent/graph.py`, keep the grounding
  safeguard (the final answer is rebuilt from the tool's raw JSON, not
  the model's free text) intact.
- This platform never gives medical advice — any change that could make
  the agent diagnose, recommend treatment, or suggest which drug to take
  will be rejected regardless of how the feature is framed.

## Reporting bugs / requesting features

Open a GitHub issue describing what you expected vs. what happened, and
how to reproduce it.

## Security issues

Please don't open a public issue for a security vulnerability — see
[SECURITY.md](SECURITY.md) instead.
