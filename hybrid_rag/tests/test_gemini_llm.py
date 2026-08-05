"""
Unit tests for app.llm.gemini_client.GeminiLLM.

Unlike tests/test_llm.py (which deliberately exercises a REAL local
Ollama daemon), these tests mock `google.genai.Client` — hitting the real
Gemini API in a test suite would require network access and burn a paid
API quota on every CI run for no extra confidence about THIS module's own
logic (message conversion, error wrapping), which is what these tests
target.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.llm.exceptions import LLMConnectionError, LLMError, LLMModelNotFoundError
from app.llm.gemini_client import GeminiLLM


def test_construction_without_api_key_raises_connection_error(monkeypatch):
    monkeypatch.setattr("app.llm.gemini_client.settings.gemini_api_key", None)
    with pytest.raises(LLMConnectionError):
        GeminiLLM(api_key=None)


def test_to_gemini_request_splits_system_and_user_messages():
    with patch("google.genai.Client"):
        llm = GeminiLLM(api_key="fake-key")

    messages = [
        {"role": "system", "content": "SYSTEM PROMPT"},
        {"role": "user", "content": "USER QUESTION"},
    ]
    system_instruction, user_content = llm._to_gemini_request(messages)

    assert system_instruction == "SYSTEM PROMPT"
    assert user_content == "USER QUESTION"


def test_generate_returns_response_text():
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.return_value = SimpleNamespace(text="Bu javob.")
        llm = GeminiLLM(api_key="fake-key")

        answer = llm.generate([{"role": "system", "content": "S"}, {"role": "user", "content": "U"}])

    assert answer == "Bu javob."
    mock_client.models.generate_content.assert_called_once()


def test_stream_yields_each_chunk_text():
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content_stream.return_value = iter(
            [SimpleNamespace(text="Sa"), SimpleNamespace(text="lom")]
        )
        llm = GeminiLLM(api_key="fake-key")

        chunks = list(llm.stream([{"role": "user", "content": "U"}]))

    assert chunks == ["Sa", "lom"]


def test_api_error_404_wrapped_as_model_not_found():
    from google.genai import errors

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = errors.APIError(
            code=404, response_json={"error": {"message": "not found"}}
        )
        llm = GeminiLLM(api_key="fake-key", model_name="not-a-real-model")

        with pytest.raises(LLMModelNotFoundError):
            llm.generate([{"role": "user", "content": "U"}])


def test_api_error_403_wrapped_as_connection_error():
    from google.genai import errors

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = errors.APIError(
            code=403, response_json={"error": {"message": "permission denied"}}
        )
        llm = GeminiLLM(api_key="fake-key")

        with pytest.raises(LLMConnectionError):
            llm.generate([{"role": "user", "content": "U"}])


def test_other_api_error_wrapped_as_generic_llm_error():
    from google.genai import errors

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = errors.APIError(
            code=500, response_json={"error": {"message": "server error"}}
        )
        llm = GeminiLLM(api_key="fake-key")

        with pytest.raises(LLMError):
            llm.generate([{"role": "user", "content": "U"}])
