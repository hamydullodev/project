"""
Configurable text-embedding wrapper for dense retrieval.

WHY THIS MODULE EXISTS
-----------------------
FAISS (Milestone 6) needs every chunk and every query converted into a
fixed-size numeric vector such that semantically similar texts land close
together in vector space. That conversion is the embedding model's job.
This module is the single place that loads the configured embedding model
(`EMBEDDING_MODEL` in `.env`) and exposes exactly two operations the rest
of the app needs — "embed a batch of documents" and "embed one query" —
so nothing downstream ever imports `sentence_transformers` directly or
needs to know which specific model is active.

WHY DOCUMENTS AND QUERIES ARE EMBEDDED DIFFERENTLY
--------------------------------------------------------
This is the single most important, least obvious fact about modern
retrieval embedding models, and getting it wrong silently degrades search
quality without any error or warning — which is exactly why it belongs
encapsulated in one tested module rather than left to every call site to
remember correctly.

Retrieval-oriented embedding models are trained on (query, passage) pairs
where the query and the passage are recognizably different kinds of text
(a short question vs. a long passage of prose), and several model
families were trained with an explicit textual marker distinguishing the
two roles:

  - **E5 family** (`intfloat/multilingual-e5-*`): REQUIRES a "query: " or
    "passage: " prefix on every input — this isn't a minor optimization,
    the model was trained with these exact prefixes and omitting them
    measurably hurts retrieval quality. This is documented directly in
    the model card and is not optional.
  - **BGE family** (`BAAI/bge-*`): the v1/v1.5 BGE models recommend an
    instruction prefix on the QUERY only ("Represent this sentence for
    searching relevant passages: "), with no prefix on documents. BGE-M3
    specifically (this project's default) was trained to work well
    *without* an instruction prefix at all (per its model card), so no
    prefix is applied for `bge-m3` — but the general BGE convention is
    still applied for other `bge-*` variants a user might configure.
  - **Everything else**: no documented prefix convention exists, so no
    prefix is applied — inventing one would be guessing, not engineering.

`_QueryDocumentPrefixer` centralizes this model-family-specific knowledge
in one place with an explicit fallback, so swapping `EMBEDDING_MODEL` in
`.env` (the spec's explicit requirement) automatically gets the right
formatting instead of silently using the wrong one for the newly
configured model.

HOW IT WORKS INTERNALLY
------------------------
`sentence-transformers` wraps a HuggingFace transformer model with its own
pooling layer (mean-pooling, CLS-token, or a learned dense layer,
depending on the specific model's config — this is baked into the model
checkpoint, not something we implement here) that reduces a variable-length
sequence of token embeddings to one fixed-size vector per input text. We
call `.encode(..., normalize_embeddings=True)`, which L2-normalizes every
output vector to unit length — required so that a plain dot product
between two vectors equals their cosine similarity, which is what FAISS's
inner-product index (Milestone 6) will compute.

The underlying `SentenceTransformer` instance is loaded once per
(model name, device) pair and cached at module scope
(`functools.lru_cache`) — constructing multiple `EmbeddingModel` objects
for the same configuration (e.g. one per Streamlit page rerun) reuses the
same in-memory weights instead of reloading a multi-gigabyte model
repeatedly.

TIME / MEMORY COMPLEXITY
-------------------------
- Model load: O(model size) one-time cost — for `bge-m3` (~2.3GB, 1024
  output dimensions) this is on the order of seconds to tens of seconds
  depending on disk speed, paid once per process thanks to the cache.
- Encoding: roughly O(n · L) where n is the number of texts and L is
  sequence length (a transformer forward pass is quadratic in sequence
  length for self-attention, but chunk texts are bounded by `CHUNK_SIZE`,
  keeping L small and roughly constant). Batching (`batch_size`) trades
  memory for throughput — larger batches use the accelerator more
  efficiently but hold more activations in memory simultaneously.
- Output memory: O(n · dim · 4 bytes) for n float32 vectors of dimension
  `dim` — for 5,000 chunks at 1024 dimensions, about 20MB; negligible.

ADVANTAGES
-----------
- Fully local and offline after the first download: the HuggingFace cache
  (`~/.cache/huggingface`) persists the model weights, satisfying "works
  completely offline after documents are indexed."
- Encapsulating the query/document prefix logic means changing
  `EMBEDDING_MODEL` in `.env` is genuinely a one-line config change, not a
  code change — exactly what the spec asks for.

DISADVANTAGES
--------------
- The device auto-detection (`cuda` > `mps` > `cpu`) assumes any detected
  accelerator works correctly for the loaded model; some operations in
  some model architectures are not yet supported on Apple's MPS backend
  and would need a fallback to `EMBEDDING_DEVICE=cpu` in `.env` if
  encountered — a known PyTorch/MPS maturity gap, not a bug in this code.
- The prefix heuristic is keyed on substrings of the model name
  (`"e5"`, `"bge"`); a model whose name doesn't contain a recognizable
  family marker gets no prefix even if it would benefit from one — a
  deliberate "don't guess" trade-off (see above).

KNOWN ISSUE: bge-m3 ON LOW-RAM MACHINES (observed on this dev machine)
---------------------------------------------------------------------------
`BAAI/bge-m3` (the original design spec's example model, ~2.3GB of
weights — NOT this project's configured default, see below) was tested
on this project's development machine — an 8GB-RAM Mac — and produced two
separate problems worth recording plainly rather than glossing over:

  1. On `EMBEDDING_DEVICE=mps`, loading hung indefinitely past the weight-
     download and weight-load stage with no forward progress, and had to
     be killed.
  2. On `EMBEDDING_DEVICE=cpu`, loading did not hang outright but showed
     classic memory-thrashing behavior (process RSS climbing to ~880MB
     then dropping back to ~370MB, CPU utilization falling to ~14%) and
     did not complete within ten minutes. `sysctl vm.swapusage` at the
     time showed 6.9GB of this machine's 8GB swap already in use — i.e.
     the machine was already under severe memory pressure before this
     process even started, and deserializing a multi-GB safetensors
     checkpoint (which needs roughly 2x the on-disk size in RAM
     transiently) pushed it into thrashing.

This is a **machine resource constraint**, not a defect in this module —
the same code loaded the smaller `paraphrase-multilingual-MiniLM-L12-v2`
(~470MB) correctly and quickly on both `mps` and `cpu` on the same
machine. If you hit this:
  - Free up RAM (close other applications) before the first `bge-m3` load.
  - Set `EMBEDDING_DEVICE=cpu` — `mps` showed the harder, indefinite hang.
  - Or switch `EMBEDDING_MODEL` to a lighter alternative for local
    development/iteration, e.g. `intfloat/multilingual-e5-base` (~1.1GB)
    or `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
    (~470MB, used by this project's own test suite for exactly this
    reason), and reserve `bge-m3` for a machine with more headroom
    (16GB+ RAM recommended for comfortable margin).

ALTERNATIVES CONSIDERED
-------------------------
- `langchain_huggingface.HuggingFaceEmbeddings`: a thinner wrapper around
  the same underlying `sentence-transformers` library; using
  `sentence-transformers` directly here keeps the prefixing/normalization
  logic visible and testable in our own code rather than hidden inside a
  third-party abstraction — valuable for an educational project where
  understanding *how* embedding works matters as much as the result.
- A remote embedding API (OpenAI, Cohere, etc.): rejected outright per the
  project's "fully local, no external API" requirement.

BEST PRACTICES APPLIED
------------------------
- Embeddings are always L2-normalized at the source (this module), so
  every downstream consumer (FAISS index, similarity scoring) can assume
  normalized vectors without re-normalizing defensively in multiple
  places.
- The model/device cache is keyed by both model name AND device, so
  switching `EMBEDDING_DEVICE` mid-process (e.g. in tests) doesn't return
  a stale instance pinned to the wrong device.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

import numpy as np

from app.config import settings
from app.utils.device import resolve_device
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default batch size for encoding many texts at once. Larger batches
# improve throughput on a GPU/MPS accelerator at the cost of more memory
# held simultaneously; 32 is a conservative default that works well on
# CPU-only machines too.
DEFAULT_BATCH_SIZE = 32

# BGE's recommended query-side instruction for the v1/v1.5 model family.
# Not applied to bge-m3, which the model card documents as not needing it.
_BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class _QueryDocumentPrefixer:
    """Applies the correct query/document text prefix for a given model family.

    See the module docstring for the reasoning behind each family's rule.
    """

    def __init__(self, model_name: str) -> None:
        self._model_name_lower = model_name.lower()

    @property
    def _is_e5(self) -> bool:
        return "e5" in self._model_name_lower

    @property
    def _is_bge_needing_instruction(self) -> bool:
        # bge-m3 explicitly does not need the instruction; other bge-*
        # models (e.g. bge-large-en) do.
        return "bge" in self._model_name_lower and "m3" not in self._model_name_lower

    def for_document(self, text: str) -> str:
        if self._is_e5:
            return f"passage: {text}"
        return text

    def for_query(self, text: str) -> str:
        if self._is_e5:
            return f"query: {text}"
        if self._is_bge_needing_instruction:
            return f"{_BGE_QUERY_INSTRUCTION}{text}"
        return text


@lru_cache(maxsize=4)
def _load_sentence_transformer(model_name: str, device: str):
    """Load (and process-wide cache) a SentenceTransformer by (name, device).

    Cached so repeated `EmbeddingModel(...)` construction (e.g. across
    Streamlit reruns, once the UI exists) reuses the already-loaded
    multi-gigabyte model instead of reloading it from disk every time.
    """
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model '%s' on device='%s' ...", model_name, device)
    model = SentenceTransformer(model_name, device=device)
    logger.info(
        "Loaded embedding model '%s': dimension=%d",
        model_name,
        _embedding_dimension(model),
    )
    return model


def _embedding_dimension(model) -> int:
    """Return the model's output dimension across sentence-transformers versions.

    `get_sentence_embedding_dimension()` was renamed to
    `get_embedding_dimension()` in a recent sentence-transformers release;
    we try the new name first and fall back to the old one so this module
    works against both the floor-pinned minimum version in
    requirements.txt and newer releases without a warning.
    """
    if hasattr(model, "get_embedding_dimension"):
        return model.get_embedding_dimension()
    return model.get_sentence_embedding_dimension()


class EmbeddingModel:
    """Loads `EMBEDDING_MODEL` and embeds documents/queries as normalized vectors."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.model_name = model_name or settings.embedding_model
        self.device = resolve_device(device or settings.embedding_device)
        self.batch_size = batch_size
        self._prefixer = _QueryDocumentPrefixer(self.model_name)
        self._model = _load_sentence_transformer(self.model_name, self.device)

    @property
    def dimension(self) -> int:
        return _embedding_dimension(self._model)

    def embed_documents(self, texts: list[str], show_progress: bool = False) -> np.ndarray:
        """Embed a batch of chunk texts for indexing.

        Returns a float32 array of shape (len(texts), dimension), L2-
        normalized so dot products equal cosine similarity.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        prefixed = [self._prefixer.for_document(t) for t in texts]
        embeddings = self._model.encode(
            prefixed,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        return embeddings.astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single user query for search.

        Returns a float32 vector of shape (dimension,), L2-normalized.
        """
        prefixed = self._prefixer.for_query(text)
        embedding = self._model.encode(
            [prefixed],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]
        return embedding.astype(np.float32)


@lru_cache(maxsize=1)
def get_default_embedding_model() -> EmbeddingModel:
    """Return the process-wide default EmbeddingModel, built from settings.

    A convenience singleton for the common case (using whatever
    `EMBEDDING_MODEL`/`EMBEDDING_DEVICE` are configured) — mirrors
    `app.config.get_settings()`'s caching pattern. Callers that need a
    non-default model/device should construct `EmbeddingModel(...)`
    directly instead.
    """
    return EmbeddingModel()
