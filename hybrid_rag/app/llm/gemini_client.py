"""
Hosted LLM access via Google's Gemini API.

WHY THIS MODULE EXISTS
-----------------------
`OllamaLLM` (ollama_client.py) documents a known limitation: this
project's small default local model (`llama3.2:3b`) can misfire on
sparse-context legal answers. `GeminiLLM` is a drop-in alternative
generation backend, selected via `LLM_PROVIDER=gemini` in `.env`
(`app/config/settings.py`), for meaningfully better instruction-following
and Uzbek-language quality at the cost of requiring network access and an
API key — a real trade-off, not a strict upgrade, which is why Ollama
remains fully supported and is still the default.

WHY THE SAME `generate()`/`stream()` INTERFACE AS `OllamaLLM`
------------------------------------------------------------------
`RAGPipeline` (app/rag/pipeline.py) only ever calls `self.llm.generate(messages)`
or `self.llm.stream(messages)` on whatever `self.llm` is — it never
imports `OllamaLLM` or `GeminiLLM` by name beyond construction. Mirroring
the exact method signatures (same input shape: a list of
`{"role": ..., "content": ...}` dicts from `app/prompts/builder.py`; same
output shape: `str` / `Iterator[str]`) means `get_llm()` (this package's
`__init__.py`) is the ONLY place that needs to know which provider is
active — swapping `LLM_PROVIDER` in `.env` needs zero pipeline code
changes, the same guarantee `OllamaLLM`'s own docstring makes for
swapping `LLM_MODEL`.

WHY MESSAGES ARE CONVERTED, NOT PASSED THROUGH
------------------------------------------------------
`build_messages()` always produces exactly two messages: one `system`
and one `user` (see that module's docstring) — Ollama's chat API shape.
Gemini's API has no `system` role in its `contents` list; a system
prompt is instead a separate `system_instruction` field on the generation
config. `_to_gemini_request()` does that one translation so nothing
upstream of this module needs to know Gemini's request shape differs
from Ollama's.

TIME / MEMORY COMPLEXITY
-------------------------
Identical reasoning to `OllamaLLM`: dominated by the remote model's own
generation time (here, network + Google's inference latency, rather than
local inference), O(1) overhead in this process beyond that.

ALTERNATIVES CONSIDERED
-------------------------
- `google-generativeai` (the older, now-legacy SDK): superseded by
  `google-genai`, the actively maintained unified SDK for both the
  Gemini Developer API and Vertex AI — using the current one avoids
  building on a deprecated dependency.
"""

from __future__ import annotations

from collections.abc import Iterator

from app.config import settings
from app.llm.exceptions import LLMConnectionError, LLMError, LLMModelNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiLLM:
    """Generates answers from chat messages using Google's Gemini API."""

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        from google import genai

        self.model_name = model_name or settings.gemini_model
        self.api_key = api_key or settings.gemini_api_key
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

        if not self.api_key:
            raise LLMConnectionError(
                "GEMINI_API_KEY is not set. Get one at https://aistudio.google.com/apikey "
                "and set it in .env (LLM_PROVIDER=gemini requires it)."
            )

        self._client = genai.Client(api_key=self.api_key)
        logger.info(
            "GeminiLLM ready: model=%s temperature=%.2f max_tokens=%d",
            self.model_name,
            self.temperature,
            self.max_tokens,
        )

    def _to_gemini_request(self, messages: list[dict[str, str]]) -> tuple[str | None, str]:
        """Split `build_messages()`'s [system, user] pair into Gemini's shape.

        Falls back to concatenating any unexpected extra messages into the
        user turn rather than raising — `build_messages()` currently only
        ever produces this exact two-message shape, but this keeps the
        conversion honest about what it actually does instead of silently
        assuming a fixed length and dropping content if that ever changes.
        """
        system_instruction: str | None = None
        user_parts: list[str] = []
        for message in messages:
            if message["role"] == "system":
                system_instruction = message["content"]
            else:
                user_parts.append(message["content"])
        return system_instruction, "\n\n".join(user_parts)

    def _config(self, system_instruction: str | None):
        from google.genai import types

        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )

    def generate(self, messages: list[dict[str, str]]) -> str:
        """Generate a complete answer from `messages` (blocking, non-streaming)."""
        from google.genai import errors

        system_instruction, user_content = self._to_gemini_request(messages)
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=user_content,
                config=self._config(system_instruction),
            )
        except errors.APIError as e:
            raise self._wrap_api_error(e) from e

        logger.info("Generated response: model=%s", self.model_name)
        return response.text or ""

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Generate an answer incrementally, yielding text chunks as produced."""
        from google.genai import errors

        system_instruction, user_content = self._to_gemini_request(messages)
        try:
            response_stream = self._client.models.generate_content_stream(
                model=self.model_name,
                contents=user_content,
                config=self._config(system_instruction),
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except errors.APIError as e:
            raise self._wrap_api_error(e) from e

    def _wrap_api_error(self, e) -> LLMError:
        from google.genai import errors

        if e.code == 404 or (isinstance(e, errors.ClientError) and "not found" in (e.message or "").lower()):
            return LLMModelNotFoundError(f"Gemini model '{self.model_name}' is not available: {e.message}")
        if e.code in (401, 403):
            return LLMConnectionError(f"Gemini API key rejected ({e.code}): {e.message}")
        return LLMError(f"Gemini API error ({e.code}): {e.message}")
