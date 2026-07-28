"""End-to-end RAG orchestration: query -> retrieve -> rerank -> prompt -> LLM -> answer."""

from app.rag.context_compression import CompressionResult, compress_context
from app.rag.evaluation import (
    GoldenQuery,
    QueryMetrics,
    evaluate_dataset,
    evaluate_query,
    mean_metrics,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.rag.query_processing import EmptyQueryError, preprocess_query
from app.rag.pipeline import RAGAnswer, RAGPipeline, RetrievalContext

__all__ = [
    "preprocess_query",
    "EmptyQueryError",
    "compress_context",
    "CompressionResult",
    "RAGPipeline",
    "RAGAnswer",
    "RetrievalContext",
    "GoldenQuery",
    "QueryMetrics",
    "evaluate_query",
    "evaluate_dataset",
    "mean_metrics",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
    "ndcg_at_k",
]
