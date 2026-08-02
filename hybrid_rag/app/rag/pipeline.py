"""
End-to-end RAG pipeline: the single class the UI actually calls.

WHY THIS MODULE EXISTS
-----------------------
Milestones 2 and 5-13 each built one well-tested, independent stage of
the spec's question-answering flow (User Question -> Query preprocessing
-> Hybrid Retrieval -> Reranking -> Context Compression -> Prompt
Construction -> Local LLM -> Answer -> Show Sources). Every prior
milestone's manual end-to-end verification wired these together by hand,
in a throwaway script, to prove the chain works. This module is that
same wiring, made permanent, tested, and reusable — `RAGPipeline` is what
the Streamlit UI (Milestones 15-19) actually imports and calls; nothing
above this module needs to know that seven other modules exist
underneath it.

WHY retrieve() AND ask() ARE SEPARATE PUBLIC METHODS
------------------------------------------------------------
`retrieve()` runs every stage EXCEPT the final LLM call (preprocess ->
hybrid retrieve -> rerank -> compress) and returns a `RetrievalContext`
holding the output of every one of those stages — not just the final
compressed chunks, but the raw hybrid results and full reranked list too.
`ask()` calls `retrieve()` and then generates an answer from it. They're
split because three different callers need different subsets of this
work:

  - The Chat page (Milestone 16) wants a full answer — calls `ask()` or
    `ask_stream()`.
  - The Retrieval Debug page (Milestone 18) wants to show HOW a query was
    retrieved and reranked, with dense/sparse/reranker scores at every
    stage, WITHOUT necessarily generating an answer (or generating one
    separately) — calls `retrieve()` alone.
  - `ask_stream()` needs the sources available immediately (to show
    "Manba 1, 2, 3..." source cards right away) while the answer text is
    still streaming in — it calls `retrieve()` first (which is fast,
    no LLM involved) and only then starts the slow streaming generation,
    rather than making the caller wait for retrieval AND the first
    streamed token as one opaque operation.

WHY AN EMPTY COMPRESSED CONTEXT SHORT-CIRCUITS BEFORE CALLING THE LLM
---------------------------------------------------------------------------
If `context.compression.kept` is empty (hybrid retrieval found nothing —
an empty index, or a question genuinely unrelated to the indexed corpus),
`ask()`/`ask_stream()` return `NOT_FOUND_MESSAGE_UZ` directly, WITHOUT
calling the LLM at all. The system prompt (Milestone 12) already
instructs the model to produce this exact message when its sources don't
answer the question — but relying on the model to reliably notice "my
context block says '(Hech qanday tegishli manba topilmadi.)'" and
correctly react to it is strictly less reliable than a direct, guaranteed
check in code for the specific situation where we ALREADY KNOW there are
zero sources. This is a stronger, code-level guarantee for the spec's
"never hallucinate" requirement in the one case (no relevant results at
all) where the answer is unambiguous — the model is still fully relied
upon for every case where SOME context was found but doesn't fully answer
the question, which is the case its instructions are actually needed for.

WHY answer_found IS A SEPARATE FIELD, NOT JUST "check the text"
------------------------------------------------------------------------
`RAGAnswer.answer_found` is computed once (checking whether
`NOT_FOUND_MESSAGE_UZ` appears in the generated text) so the UI (e.g. to
decide whether to show a "no results" styling vs. a normal answer card)
never needs to re-implement or import that check itself — the same
"compute once, expose as data" principle used throughout this pipeline
(e.g. `HybridSearchResult`/`RerankedResult` precomputing every score
rather than making the UI recompute them).

TIME / MEMORY COMPLEXITY
-------------------------
Dominated entirely by whichever prior-milestone stage is slowest for a
given query — typically LLM generation (seconds, proportional to output
length) exceeds retrieval + reranking + compression (tens of
milliseconds total, per those modules' own complexity analyses) by one
to two orders of magnitude. This module adds no algorithmic work of its
own beyond passing data between stages.

ADVANTAGES
-----------
- One class, constructed once, is the entire public surface the UI needs
  — swapping any underlying component (a different embedding model, a
  different LLM) requires no UI code changes, only `.env`.
- `RetrievalContext` preserves full provenance from every stage (dense/
  sparse/combined/reranker scores, what was deduplicated, what was
  dropped for budget) — the Retrieval Debug page (Milestone 18) is
  "render this object," not a parallel data-collection effort.

DISADVANTAGES
--------------
- `RAGPipeline.__init__` eagerly loads/constructs every component
  (embedding model, reranker, LLM connection check) — meaningful startup
  latency (each of Milestones 5 and 9's models takes real seconds to
  load). Acceptable because the Streamlit UI (Milestones 15+) will
  construct this once per session via a cached resource, not once per
  question.
- No conversation memory — each `ask()`/`ask_stream()` call is
  independent, matching `build_messages`'s single-turn design (Milestone
  12); multi-turn context is a documented future extension point for the
  Chat page, not implemented here.

ALTERNATIVES CONSIDERED
-------------------------
- A single `ask()` method with a `stream: bool` parameter instead of two
  methods: rejected for the same reason `OllamaLLM.generate`/`.stream`
  are separate (Milestone 13) — the return type genuinely differs
  (`RAGAnswer` vs. `(RetrievalContext, Iterator[str])`), and a caller
  reading the method name should know what they're getting without
  inspecting a flag.

BEST PRACTICES APPLIED
------------------------
- Every component (repo, embedding model, vector store, BM25 index,
  reranker, LLM) is constructor-injectable, defaulting to loading from
  configured settings — the same dependency-injection pattern
  `IndexingPipeline` (Milestone 10) uses, for the same testability
  reason: tests construct a `RAGPipeline` over a small in-memory corpus
  and a real (but tiny/fast) model stack, never touching the real
  project's `indexes/`/`data/` directories.
"""

from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel

from app.config import settings
from app.database import MetadataRepository
from app.llm import GeminiLLM, OllamaLLM, get_llm
from app.prompts import NOT_FOUND_MESSAGE_UZ, build_messages
from app.rag.context_compression import CompressionResult, compress_context
from app.rag.query_processing import preprocess_query
from app.reranker import RerankedResult, RerankerModel
from app.retriever import (
    BM25IndexError,
    BM25SparseIndex,
    EmbeddingModel,
    FAISSVectorStore,
    HybridRetriever,
    HybridSearchResult,
    VectorStoreError,
    get_default_embedding_model,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RetrievalContext(BaseModel):
    """Everything produced by every pipeline stage before the LLM is called.

    Kept in full (not just the final compressed chunks) so the Retrieval
    Debug page (Milestone 18) can show a query's entire journey — how
    many candidates each of dense/sparse search found, what reranking did
    to their order, and what compression kept or dropped, and why.
    """

    query: str
    hybrid_results: list[HybridSearchResult]
    reranked: list[RerankedResult]
    compression: CompressionResult


class RAGAnswer(BaseModel):
    """A generated answer with its sources and whether anything was actually found."""

    query: str
    answer: str
    sources: list[RerankedResult]
    answer_found: bool


class RAGPipeline:
    """Orchestrates the full question-answering flow over every prior milestone's components."""

    def __init__(
        self,
        repo: MetadataRepository | None = None,
        embedding_model: EmbeddingModel | None = None,
        vector_store: FAISSVectorStore | None = None,
        bm25_index: BM25SparseIndex | None = None,
        reranker: RerankerModel | None = None,
        llm: OllamaLLM | GeminiLLM | None = None,
    ) -> None:
        self.repo = repo or MetadataRepository()
        self.embedding_model = embedding_model or get_default_embedding_model()

        if vector_store is not None:
            self.vector_store = vector_store
        else:
            try:
                self.vector_store = FAISSVectorStore.load()
            except VectorStoreError as e:
                logger.warning("No usable FAISS index on disk (%s); starting with an empty index.", e)
                self.vector_store = FAISSVectorStore(dimension=self.embedding_model.dimension)

        if bm25_index is not None:
            self.bm25_index = bm25_index
        else:
            try:
                self.bm25_index = BM25SparseIndex.load()
            except BM25IndexError as e:
                logger.warning("No usable BM25 index on disk (%s); starting empty.", e)
                self.bm25_index = BM25SparseIndex()

        self.retriever = HybridRetriever(self.vector_store, self.bm25_index, self.embedding_model)
        self.reranker = reranker or RerankerModel()
        self.llm = llm or get_llm()

        logger.info(
            "RAGPipeline ready: %d vector(s), %d BM25 chunk(s)",
            len(self.vector_store),
            len(self.bm25_index),
        )

    def retrieve(self, raw_query: str, collection_ids: list[str] | None = None) -> RetrievalContext:
        """Preprocess, hybrid-retrieve, rerank, and compress — no LLM call.

        Raises `EmptyQueryError` (from `preprocess_query`) for empty or
        whitespace-only input, propagated to the caller rather than
        swallowed, so the UI can show a specific "enter a question"
        message.

        `collection_ids`, when given, scopes retrieval to only those
        collections (see `app/config/collections.py`) — e.g. "search only
        Oila kodeksi", or several ids at once for cross-code search
        (spec: search Family Code + Guardianship Law + Child Rights Law
        together, combined into one ranked list). This is implemented as
        a POST-filter on hybrid search results, not a FAISS/BM25-level
        filtered search (see `app/retriever/hybrid_retriever.py` — neither
        index supports metadata filtering natively without a much larger
        architectural change, not justified at this corpus size). Because
        filtering happens after the union of dense+sparse top-`top_k`
        candidates, a narrow collection scope could otherwise be starved
        of candidates if `top_k` weren't widened first — `top_k` is
        multiplied by `settings.retrieval_filter_oversample` whenever a
        scope is active, so reranking still sees a reasonably sized pool.
        """
        query = preprocess_query(raw_query)

        effective_top_k = settings.top_k
        if collection_ids:
            effective_top_k = settings.top_k * settings.retrieval_filter_oversample

        hybrid_results = self.retriever.retrieve(query, top_k=effective_top_k)

        chunk_ids = [r.chunk_id for r in hybrid_results]
        chunks_by_id = {c.id: c for c in self.repo.get_chunks_by_ids(chunk_ids)}

        if collection_ids:
            allowed = set(collection_ids)
            hybrid_results = [
                r
                for r in hybrid_results
                if (chunk := chunks_by_id.get(r.chunk_id)) is not None and chunk.collection_id in allowed
            ]

        reranked = self.reranker.rerank(query, hybrid_results, chunks_by_id, top_k=settings.rerank_top_k)

        compression = compress_context(reranked)

        return RetrievalContext(
            query=query, hybrid_results=hybrid_results, reranked=reranked, compression=compression
        )

    def ask(self, raw_query: str, collection_ids: list[str] | None = None) -> RAGAnswer:
        """Answer `raw_query`, generating a complete (non-streaming) response."""
        context = self.retrieve(raw_query, collection_ids=collection_ids)

        if not context.compression.kept:
            logger.info("No relevant sources found for query=%r; skipping LLM call.", context.query)
            return RAGAnswer(query=context.query, answer=NOT_FOUND_MESSAGE_UZ, sources=[], answer_found=False)

        messages = build_messages(context.query, context.compression.kept)
        answer_text = self.llm.generate(messages)

        return RAGAnswer(
            query=context.query,
            answer=answer_text,
            sources=context.compression.kept,
            answer_found=NOT_FOUND_MESSAGE_UZ not in answer_text,
        )

    def stream_from_context(self, context: RetrievalContext) -> Iterator[str]:
        """Stream an answer for an ALREADY-RETRIEVED `RetrievalContext`.

        Split out from `ask_stream()` (which still calls this) so a caller
        that needs `retrieve()` and the streaming LLM call to happen at
        DIFFERENT points can do so — the motivating case is the FastAPI
        backend (`api/routers/ask.py`, added alongside the Next.js
        frontend): an HTTP route must be able to return a synchronous
        400/503 error for a retrieval-time failure (e.g. `EmptyQueryError`)
        BEFORE it starts a streaming response — once a `StreamingResponse`
        begins, the HTTP status code is already committed and can't be
        changed. That route calls `retrieve()` itself, handles its own
        errors with proper status codes, and only calls this method once
        it's ready to commit to streaming.
        """
        if not context.compression.kept:
            logger.info("No relevant sources found for query=%r; skipping LLM call.", context.query)
            return iter([NOT_FOUND_MESSAGE_UZ])

        messages = build_messages(context.query, context.compression.kept)
        return self.llm.stream(messages)

    def ask_stream(
        self, raw_query: str, collection_ids: list[str] | None = None
    ) -> tuple[RetrievalContext, Iterator[str]]:
        """Answer `raw_query`, streaming the answer text as it's generated.

        Returns `(context, stream)` — `context` (including sources) is
        available immediately, since retrieval/reranking/compression
        happen before this method returns; `stream` is a generator that
        produces the answer's text incrementally as the caller iterates
        it (what the Chat UI, Milestone 16, needs for a typing effect).
        """
        context = self.retrieve(raw_query, collection_ids=collection_ids)
        return context, self.stream_from_context(context)
