<div align="center">

# ⚖️ UzLaw AI

Local, cited, hybrid-RAG legal assistant for Uzbekistan's legal codes.

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=next.js&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=for-the-badge)
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-64748b?style=for-the-badge" alt="MIT License"/></a>

</div>

---

## Features

⚖️ Legal Question Answering
📄 Hybrid RAG
🔍 Semantic Search
🧠 Local LLM
📚 Source Citation
🚀 Fast Retrieval

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-black?style=flat-square)
![Llama 3.2](https://img.shields.io/badge/Llama_3.2-0467DF?style=flat-square)
![FAISS](https://img.shields.io/badge/FAISS-4f8ef7?style=flat-square)
![Sentence Transformers](https://img.shields.io/badge/Sentence_Transformers-FFD21E?style=flat-square)
![BM25](https://img.shields.io/badge/BM25-4f8ef7?style=flat-square)
![Hybrid RAG](https://img.shields.io/badge/Hybrid_RAG-7C5CFF?style=flat-square)
![LoRA](https://img.shields.io/badge/LoRA_Fine--tuning-7C5CFF?style=flat-square)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![Unsloth](https://img.shields.io/badge/Unsloth-black?style=flat-square)

---

## Project Structure

```
hybrid_rag/
├── app/            # RAG core: ingestion, retriever, reranker, llm
├── api/            # FastAPI backend (SSE streaming)
├── frontend/       # Next.js product UI
├── docs/           # Architecture & evaluation docs
└── tests/          # Pipeline & retrieval-quality tests
```

---

## Architecture

```mermaid
flowchart TD
    A[User] --> B[Frontend]
    B --> C[FastAPI]
    C --> D[Hybrid Retriever]
    D --> E[FAISS + BM25]
    E --> F[Local LLM · LoRA Fine-tuned]
    F --> G[Answer + Sources]

    style A fill:#7C5CFF,color:#fff,stroke:none
    style F fill:#4f8ef7,color:#fff,stroke:none
    style G fill:#22c55e,color:#fff,stroke:none
```

---

## Demo

<div align="center">
<img src="docs/demo.gif" width="100%" alt="UzLaw AI demo"/>
</div>

---

## How it Works

1. User asks
2. Hybrid Retrieval
3. Re-ranking
4. Local LLM generates
5. Sources returned

---

## Fine-Tuning

Fine-tuned using **LoRA**.

- **Base Model:** Llama 3.2 / Qwen 2.5
- **Dataset:** Alpaca-format instruction data
- **Unsloth** for efficient training
- **PEFT** + **LoRA** adapters
- **Hugging Face Transformers** + **PyTorch**

---

## Results

| Metric | Value |
|---|---|
| Retrieval Accuracy (nDCG@5) | 0.77 |
| Latency | Local, hardware-dependent |
| Context Length | 128K (Llama 3.2) |

---

## License

MIT

