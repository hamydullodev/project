.PHONY: help setup setup-dev api frontend streamlit test test-eval lint format

help:
	@echo "Common commands:"
	@echo "  make setup       — create venv, install runtime deps, install frontend deps"
	@echo "  make setup-dev   — also install dev tooling (ruff/black/isort/mypy)"
	@echo "  make api         — run the FastAPI backend (:8000)"
	@echo "  make frontend    — run the Next.js dev server (:3000)"
	@echo "  make streamlit   — run the internal Streamlit debug tool (:8501)"
	@echo "  make test        — run the Python test suite"
	@echo "  make test-eval   — run retrieval-quality evaluation metrics only"
	@echo "  make lint        — ruff + mypy (Python), eslint (frontend)"
	@echo "  make format      — black + isort (Python)"

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd frontend && npm install

setup-dev: setup
	.venv/bin/pip install -r requirements-dev.txt

api:
	.venv/bin/python run_api.py

frontend:
	cd frontend && npm run dev

streamlit:
	.venv/bin/python run.py

test:
	.venv/bin/python -m pytest

test-eval:
	.venv/bin/python -m pytest tests/evaluation/ -v

lint:
	.venv/bin/ruff check app api tests run.py run_api.py
	.venv/bin/mypy app api
	cd frontend && npm run lint

format:
	.venv/bin/black app api tests run.py run_api.py
	.venv/bin/isort app api tests run.py run_api.py
