# Contributing

Thanks for considering a contribution to Fine-Tuning Studio.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Workflow

1. Fork and branch from `main`.
2. Keep changes focused — one logical change per PR.
3. Add or update tests under `tests/` for anything in `scripts/`, `training/dataset_utils.py`, or `configs/`.
4. Run `pytest` before opening a PR — CI runs the same suite.
5. Describe *why* in the PR description, not just *what*.

## Code style

- No comments explaining *what* the code does — names should do that. Comment only non-obvious *why*.
- Prefer small, direct functions over speculative abstractions.
- Match the existing config-driven pattern (`configs/*.yaml`) rather than hardcoding hyperparameters.

## Reporting bugs / requesting features

Open a GitHub issue with:
- What you expected vs. what happened
- Steps to reproduce (dataset size, mode `lora`/`qlora`, model, GPU)
- Relevant log output

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities instead.
