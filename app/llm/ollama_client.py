"""
Local LLM access via Ollama.

WHY THIS MODULE EXISTS
-----------------------
Every prior milestone in the question-answering pipeline (retrieval,
reranking, compression, prompt construction) produces a list of chat
messages. Something has to actually generate an answer from them. The
spec requires this generator be a local model served by Ollama, with the
specific model configurable via `LLM_MODEL` in `.env` — this module is
the one place that talks to Ollama, so nothing else in the app needs to
know whether the configured model is Llama, Qwen, Mistral, Gemma, or
DeepSeek (all named as supported examples in the spec): Ollama's chat API
is uniform across all of them, and this wrapper is equally uniform.

WHY THE OFFICIAL `ollama` PYTHON PACKAGE INSTEAD OF RAW HTTP
--------------------------------------------------------------------
Ollama exposes a local REST API, which this module could call directly
via `httpx`/`requests`. The official `ollama` package is used instead
because it already handles request/response (de)serialization into typed
objects, connection-error wrapping (verified empirically: a connection
failure surfaces as a plain, already-descriptive `ConnectionError`
telling the user to check that Ollama is running), and streaming
iteration correctly — reimplementing that against the raw HTTP API would
just be re-deriving what the maintained client already does correctly.

WHY MODEL AVAILABILITY IS CHECKED AT CONSTRUCTION, NOT JUST ON FIRST USE
--------------------------------------------------------------------------------
`OllamaLLM.__init__` calls `ollama.Client.list()` and checks the
configured `LLM_MODEL` is present, raising `LLMModelNotFoundError` with
the exact `ollama pull <model>` command to fix it, immediately at
construction time. Without this, a misconfigured `LLM_MODEL` would only
surface as a failure deep inside the first `generate()`/`stream()` call —
likely well after the rest of a RAG pipeline (retrieval, reranking) has
already done real work — instead of failing fast, clearly, and cheaply
(a `list()` call is a fast local round-trip, not a generation request)
before any of that work is attempted. Every call site is still defended
individually too (see below), since a model could in principle be
deleted between construction and use.

WHY STREAMING IS A SEPARATE METHOD, NOT A FLAG
------------------------------------------------------
`generate()` returns a plain `str` (the complete answer) for callers that
just need the final text (an evaluation script, Milestone 20's retrieval-
quality tests). `stream()` is a generator yielding incremental text
chunks as Ollama produces them — what the Chat UI (Milestone 16) needs
for its "streaming answer, typing animation" requirement. Splitting these
into two methods with different return types (`str` vs `Iterator[str]`)
is clearer at every call site than one method with a `stream: bool` flag
whose return type depends on an argument value — a caller reading
`llm.generate(messages)` or `for chunk in llm.stream(messages):` knows
exactly what they're getting without checking a flag's value.

TIME / MEMORY COMPLEXITY
-------------------------
Generation time is dominated by the model itself (proportional to output
token count and the model's size/quantization — entirely outside this
module's control), typically seconds on CPU/MPS for a small local model.
This wrapper's own overhead is O(1): serializing the message list and
deserializing the response. Memory usage in THIS process is minimal — the
model's weights live in the separate Ollama server process, not in the
Python process running this code (unlike the embedding/reranker models
from Milestones 5 and 9, which load weights directly into this process).

ADVANTAGES
-----------
- Swapping `LLM_MODEL` in `.env` (the spec's explicit requirement) needs
  zero code changes — Ollama's chat API and this wrapper are identical
  regardless of which supported model is configured.
- Fails fast and specifically: a missing Ollama connection and a missing
  model are two DIFFERENT, clearly-worded errors, not one generic
  failure a user has to guess the cause of.

DISADVANTAGES
--------------
- No token-level control beyond `temperature`/`num_predict` (max output
  tokens) is exposed — sufficient for this project's needs, but Ollama's
  `options` dict supports many more generation parameters
  (`top_p`, `top_k`, `repeat_penalty`, ...) that aren't surfaced here to
  keep the configuration surface (`.env`) focused on what actually needs
  tuning for this use case.
- The construction-time availability check adds a small fixed latency
  (one local API round-trip) to every `OllamaLLM(...)` construction —
  negligible next to model generation time, and outweighed by failing
  fast with a clear message instead of a confusing failure later.

ALTERNATIVES CONSIDERED
-------------------------
- `langchain_community.llms.Ollama` / `langchain_ollama`: a LangChain-
  wrapped equivalent: would fit this project's existing LangChain usage
  elsewhere (text splitting), but adds an abstraction layer between this
  code and Ollama's actual API — using the official `ollama` package
  directly keeps the request/response shape (and its error handling)
  visible and easy to reason about, valuable for an educational project.
- A remote hosted LLM API (OpenAI, Anthropic, etc.): rejected outright
  per the project's "fully local, no external API" requirement — the
  entire reason Ollama is the only supported backend here.

BEST PRACTICES APPLIED
------------------------
- Every public method wraps Ollama-specific exceptions
  (`ConnectionError`, `ollama.ResponseError`) into this project's own
  `LLMConnectionError`/`LLMModelNotFoundError`/`LLMError` hierarchy
  (`app.llm.exceptions`) at the boundary, so no caller anywhere else in
  the app needs to import or know about the `ollama` package's own
  exception types.
- Generation parameters (`temperature`, `max_tokens`) default to
  `.env`-configured values but can be overridden per call site via the
  constructor, the same pattern `EmbeddingModel` and `RerankerModel` use.
"""

from __future__ import annotations

from typing import Iterator, Optional

from app.config import settings
from app.llm.exceptions import LLMConnectionError, LLMError, LLMModelNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def list_available_models(base_url: Optional[str] = None) -> list[str]:
    """Return the tags of every model currently pulled in the local Ollama instance.

    A standalone helper (not tied to one `OllamaLLM` instance) since the
    Settings/Home page (later milestones) needs this independent of
    which specific model is configured as `LLM_MODEL`, e.g. to let a
    user pick from what's actually available.
    """
    import ollama

    client = ollama.Client(host=base_url or settings.ollama_base_url)
    try:
        response = client.list()
    except ConnectionError as e:
        raise LLMConnectionError(str(e)) from e
    return [m.model for m in response.models]


class OllamaLLM:
    """Generates answers from chat messages using a local Ollama-served model."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        import ollama

        self.model_name = model_name or settings.llm_model
        self.base_url = base_url or settings.ollama_base_url
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

        self._client = ollama.Client(host=self.base_url)
        self._verify_model_available()
        logger.info(
            "OllamaLLM ready: model=%s base_url=%s temperature=%.2f max_tokens=%d",
            self.model_name,
            self.base_url,
            self.temperature,
            self.max_tokens,
        )

    def _verify_model_available(self) -> None:
        available = list_available_models(self.base_url)
        if self.model_name not in available:
            raise LLMModelNotFoundError(
                f"Model '{self.model_name}' is not available locally. "
                f"Pull it first with: ollama pull {self.model_name}\n"
                f"Currently available models: {sorted(available) or '(none)'}"
            )

    def _options(self) -> dict:
        return {"temperature": self.temperature, "num_predict": self.max_tokens}

    def generate(self, messages: list[dict[str, str]]) -> str:
        """Generate a complete answer from `messages` (blocking, non-streaming)."""
        import ollama

        try:
            response = self._client.chat(
                model=self.model_name, messages=messages, options=self._options()
            )
        except ConnectionError as e:
            raise LLMConnectionError(str(e)) from e
        except ollama.ResponseError as e:
            raise self._wrap_response_error(e) from e

        logger.info(
            "Generated response: model=%s eval_count=%s",
            self.model_name,
            getattr(response, "eval_count", "?"),
        )
        return response.message.content

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Generate an answer incrementally, yielding text chunks as produced.

        Used by the Chat UI (Milestone 16) for a streaming, "typing"
        response instead of waiting for the full answer before showing
        anything.
        """
        import ollama

        try:
            response_stream = self._client.chat(
                model=self.model_name,
                messages=messages,
                stream=True,
                options=self._options(),
            )
            for chunk in response_stream:
                if chunk.message.content:
                    yield chunk.message.content
        except ConnectionError as e:
            raise LLMConnectionError(str(e)) from e
        except ollama.ResponseError as e:
            raise self._wrap_response_error(e) from e

    def _wrap_response_error(self, e) -> LLMError:
        if getattr(e, "status_code", None) == 404:
            return LLMModelNotFoundError(
                f"Model '{self.model_name}' is not available locally. "
                f"Pull it first with: ollama pull {self.model_name}"
            )
        return LLMError(str(e))
