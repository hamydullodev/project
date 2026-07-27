"""Dense (FAISS) and sparse (BM25) retrieval, and their hybrid fusion."""

from app.retriever.embeddings import EmbeddingModel, get_default_embedding_model
from app.retriever.vector_store import FAISSVectorStore, VectorStoreError

__all__ = [
    "EmbeddingModel",
    "get_default_embedding_model",
    "FAISSVectorStore",
    "VectorStoreError",
]
