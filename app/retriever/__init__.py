"""Dense (FAISS) and sparse (BM25) retrieval, and their hybrid fusion."""

from app.retriever.embeddings import EmbeddingModel, get_default_embedding_model
from app.retriever.vector_store import FAISSVectorStore, VectorStoreError
from app.retriever.bm25_index import BM25SparseIndex, BM25IndexError
from app.retriever.tokenizer import tokenize
from app.retriever.hybrid_retriever import HybridRetriever, HybridSearchResult

__all__ = [
    "EmbeddingModel",
    "get_default_embedding_model",
    "FAISSVectorStore",
    "VectorStoreError",
    "BM25SparseIndex",
    "BM25IndexError",
    "tokenize",
    "HybridRetriever",
    "HybridSearchResult",
]
