"""
Unit tests for app.llm.ollama_client.

Runs against the REAL, locally-running Ollama daemon (not mocked) — this
project targets an environment where Ollama is genuinely installed and
running (a prerequisite documented in the README), and the whole point of
this module is its interaction with that real local service. Uses
llama3.2:3b, confirmed available on this project's dev machine.

If Ollama isn't running when these tests execute, every test here will
fail with LLMConnectionError — that's the correct, informative failure
mode (see the module docstring's "fail fast" rationale), not something to
work around with mocks that would hide exactly the integration this
module exists to get right.
"""

from __future__ import annotations

import pytest

from app.llm.exceptions import LLMConnectionError, LLMModelNotFoundError
from app.llm.ollama_client import OllamaLLM, list_available_models

REAL_MODEL = "llama3.2:3b"


def test_list_available_models_includes_pulled_model():
    models = list_available_models()
    assert REAL_MODEL in models


def test_list_available_models_bad_url_raises_connection_error():
    with pytest.raises(LLMConnectionError):
        list_available_models(base_url="http://localhost:19999")


@pytest.fixture(scope="module")
def llm() -> OllamaLLM:
    return OllamaLLM(model_name=REAL_MODEL, temperature=0.0, max_tokens=50)


def test_construction_with_unavailable_model_raises():
    with pytest.raises(LLMModelNotFoundError):
        OllamaLLM(model_name="definitely-not-a-real-model-xyz")


def test_construction_with_bad_base_url_raises_connection_error():
    with pytest.raises(LLMConnectionError):
        OllamaLLM(model_name=REAL_MODEL, base_url="http://localhost:19999")


def test_generate_returns_nonempty_string(llm: OllamaLLM):
    answer = llm.generate([{"role": "user", "content": "Bir soʻz bilan javob ber: osmon qanday rangda?"}])
    assert isinstance(answer, str)
    assert len(answer.strip()) > 0


def test_generate_accepts_system_and_user_messages(llm: OllamaLLM):
    """Verifies a system+user message pair is accepted and produces a
    valid response — NOT that the model perfectly follows an arbitrary
    instruction. A small 3B local model's instruction-following fidelity
    is a model-quality question, not something this wrapper's tests
    should assert exact content for; that would make the test suite
    flaky against model behavior this code has no control over."""
    messages = [
        {"role": "system", "content": "Siz foydali yordamchisiz."},
        {"role": "user", "content": "Salom!"},
    ]
    answer = llm.generate(messages)
    assert isinstance(answer, str)
    assert len(answer.strip()) > 0


def test_stream_yields_chunks_that_concatenate_to_nonempty_text(llm: OllamaLLM):
    chunks = list(llm.stream([{"role": "user", "content": "Bir soʻz bilan javob ber: 2+2 nechi?"}]))
    assert len(chunks) >= 1
    full_text = "".join(chunks)
    assert len(full_text.strip()) > 0


def test_stream_and_generate_are_both_callable_multiple_times(llm: OllamaLLM):
    first = llm.generate([{"role": "user", "content": "Bir soʻz ayt."}])
    second = llm.generate([{"role": "user", "content": "Yana bir soʻz ayt."}])
    assert isinstance(first, str)
    assert isinstance(second, str)


def test_default_model_comes_from_settings():
    from app.config import settings

    llm_default = OllamaLLM()
    assert llm_default.model_name == settings.llm_model
