# Hybrid RAG — O'zbekiston qonunchiligi (Uzbek Law)

A fully local, offline Hybrid Retrieval-Augmented Generation system for
answering legal questions in Uzbek, grounded in the actual text of Uzbek
legal codes (no cloud APIs, no external services after setup).

> **Status:** Milestone 1 of 20 complete (project scaffolding & config).
> This README grows with each milestone.

## Why "hybrid"?

Retrieval combines two complementary search strategies:
- **Dense retrieval** (FAISS + multilingual sentence embeddings) — good at
  matching *meaning* even when wording differs from the source text.
- **Sparse retrieval** (BM25) — good at matching *exact legal terms and
  article numbers*, which dense embeddings can blur.

Results from both are fused, then reranked with a cross-encoder for a final
precision pass before being handed to a local LLM (via Ollama) to generate
a grounded, cited answer.

## Corpus

`documents/raw/` currently contains five Uzbek legal codes as plain text:

| File | Code |
|---|---|
| `fuqorolik.txt` | Fuqarolik kodeksi (Civil Code) |
| `fuqorolik_protsessual.txt` | Fuqarolik protsessual kodeksi (Civil Procedure Code) |
| `iqtisodiy_protsessual.txt` | Iqtisodiy protsessual kodeksi (Economic Procedure Code) |
| `jinoyat.txt` | Jinoyat kodeksi (Criminal Code) |
| `mehnat.txt` | Mehnat kodeksi (Labor Code) |

New documents (PDF, DOCX, TXT, HTML) can be added later without touching
any code — see the Upload/Index pages (coming in later milestones).

## Project structure

```
hybrid_rag/
├── app/
│   ├── config/       # Pydantic settings, loaded from .env
│   ├── utils/         # Logging and shared helpers
│   ├── database/       # SQLite metadata layer
│   ├── ingestion/       # Document loaders, cleaning, chunking
│   ├── retriever/        # FAISS (dense) + BM25 (sparse) + fusion
│   ├── reranker/          # Cross-encoder reranking
│   ├── llm/                # Local LLM access (Ollama)
│   ├── prompts/              # Prompt templates
│   ├── rag/                    # End-to-end pipeline orchestration
│   └── ui/                      # Streamlit pages
├── data/               # SQLite DB (generated)
├── indexes/            # FAISS + BM25 indexes (generated)
├── documents/           # Source documents (raw/ + uploaded/)
├── notebooks/            # Exploratory notebooks
├── tests/                  # Unit tests + retrieval evaluation
├── requirements.txt
├── .env.example
└── run.py
```

## Setup

```bash
cd hybrid_rag
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit .env if you want non-default models

python run.py                      # smoke-tests configuration loading
```

### Local LLM (Ollama)

This project generates answers with a model served locally by
[Ollama](https://ollama.com). Install Ollama, then pull a model:

```bash
ollama pull llama3.2:3b            # or qwen2.5, mistral, gemma2, deepseek-r1 ...
```

Set `LLM_MODEL` in `.env` to match whichever tag you pulled.

### A note on RAM and the embedding model

The spec's example embedding model, `BAAI/bge-m3`, is ~2.3GB of weights
and needs roughly double that in RAM transiently while loading. On this
project's own 8GB-RAM development machine, loading `bge-m3` hung
indefinitely on `EMBEDDING_DEVICE=mps` and thrashed (severe swapping,
10+ minutes without completing) on `EMBEDDING_DEVICE=cpu` — the machine
was already low on free RAM, and a multi-GB model load pushed it into
swap. This is a resource constraint, not a bug: smaller models (see
below) loaded quickly and correctly on the same machine.

If you hit this on your own machine:
- Close other memory-heavy applications before the first `bge-m3` load
  (subsequent loads reuse the HuggingFace cache, but still need the RAM
  headroom to deserialize the checkpoint into memory each process start).
- Prefer `EMBEDDING_DEVICE=cpu` over `mps` — `mps` produced an outright
  hang in testing, `cpu` at least made (slow) forward progress.
- For local development/iteration, consider a lighter model:
  `intfloat/multilingual-e5-base` (~1.1GB) or
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (~470MB —
  this is what the project's own test suite uses for exactly this
  reason). Reserve `bge-m3` / `multilingual-e5-large` for a machine with
  16GB+ RAM.

## Configuration

All configuration lives in `.env` (see `.env.example` for every key and its
default). Highlights:

| Variable | Purpose |
|---|---|
| `LLM_MODEL` | Ollama model tag used for generation |
| `EMBEDDING_MODEL` | Multilingual embedding model for dense retrieval |
| `RERANKER_MODEL` | Cross-encoder used to rerank hybrid results |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Text splitting parameters |
| `TOP_K` / `RERANK_TOP_K` | Candidates before/after reranking |
| `DENSE_WEIGHT` / `SPARSE_WEIGHT` | Hybrid score fusion weights |
| `VECTOR_PATH` / `BM25_PATH` / `SQLITE_PATH` | Where indexes/metadata are stored |

## Roadmap

Built in 20 milestones — see the project task list for current progress.
Each milestone adds working, tested code plus an explanation of *why* the
module exists, *how* it works, its complexity, and trade-offs (this is an
educational project).

## License / data source note

The included legal texts are Uzbekistan's public legal codes. Verify
against an official source (e.g. lex.uz) before relying on any answer this
system produces for real legal decisions — this is an educational retrieval
system, not legal advice.
