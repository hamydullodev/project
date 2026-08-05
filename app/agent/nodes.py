"""LangGraph node implementations (LLM call, tool execution, formatting)."""

from __future__ import annotations

import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from app.agent.planner import resolve_relative_dates
from app.agent.prompts import build_system_prompt
from app.agent.state import AgentState
from app.config import get_settings
from app.tools import ALL_TOOLS
from app.utils.logger import get_logger

logger = get_logger(__name__)

_model = None

# A small local model will sometimes ignore "narx mavjud emas" in a tool
# result and narrate a plausible-looking price anyway. Since the PDF spec's
# hardest rule is "LLM never invents flight facts", we can't just trust the
# prompt for this — we verify the final answer against the tool output it
# was supposedly built from, and override it if it invented a price.
_CURRENCY_PATTERN = re.compile(
    r"\d[\d\s.,]{1,12}\s?(so'?m|so‘m|uzs|usd|eur|try|aed|gbp|rub|\$|€)",
    re.IGNORECASE,
)

# web_search answers are only trustworthy if the user can click through to
# the actual page — a paraphrase with no link is unverifiable. The model
# reliably drops links when summarizing, so sources are re-attached in code
# instead of trusting the prompt to remember them every time.
_URL_PATTERN = re.compile(r"https?://\S+")


def _get_model():
    global _model
    if _model is None:
        settings = get_settings()
        _model = ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
        ).bind_tools(ALL_TOOLS)
    return _model


def _find_price_unavailable_tool_message(messages: list) -> ToolMessage | None:
    """Find the most recent ToolMessage (this turn) that reported no price."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return None
        if isinstance(message, ToolMessage) and "narx mavjud emas" in str(message.content).lower():
            return message
    return None


def _sanitize_final_answer(response: AIMessage, messages: list) -> AIMessage:
    """Override a fabricated price with the actual (price-less) tool data."""
    if getattr(response, "tool_calls", None):
        return response

    tool_message = _find_price_unavailable_tool_message(messages)
    if tool_message is None or not _CURRENCY_PATTERN.search(str(response.content)):
        return response

    logger.warning("Model fabricated a price despite the tool reporting none — overriding with raw tool data.")
    safe_content = (
        "⚠️ Ushbu yo'nalish uchun narx ma'lumoti mavjud emas — aktiv provayder narx "
        "taqdim etmaydi. Quyida haqiqiy API natijasi:\n\n" + str(tool_message.content)
    )
    return response.model_copy(update={"content": safe_content})


_WEB_SOURCED_TOOLS = {"web_search", "recommend_destination_guide"}


def _find_web_search_tool_message(messages: list) -> ToolMessage | None:
    """Find the most recent web-sourced ToolMessage in this turn, if any."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return None
        if isinstance(message, ToolMessage) and message.name in _WEB_SOURCED_TOOLS:
            return message
    return None


def _append_sources(response: AIMessage, messages: list) -> AIMessage:
    """Attach the real source links whenever the answer relied on a web search.

    The model routinely drops the URLs when paraphrasing search results, but
    a web-sourced claim (visa rules, safety advisories, ...) is only
    verifiable if the user can click through to where it came from.
    """
    if getattr(response, "tool_calls", None):
        return response

    tool_message = _find_web_search_tool_message(messages)
    if tool_message is None:
        return response

    raw_links = _URL_PATTERN.findall(str(tool_message.content))
    links = list(dict.fromkeys(link.rstrip(").,;") for link in raw_links))
    if not links or _URL_PATTERN.search(str(response.content)):
        return response

    sources = "\n".join(f"- {link}" for link in links[:5])
    safe_content = f"{response.content}\n\n**Manbalar:**\n{sources}"
    return response.model_copy(update={"content": safe_content})


def call_model(state: AgentState) -> dict:
    """Invoke the local LLM (with tools bound) on the current message history."""
    messages = state["messages"]

    if messages and isinstance(messages[-1], HumanMessage):
        messages = [
            *messages[:-1],
            HumanMessage(content=resolve_relative_dates(str(messages[-1].content))),
        ]

    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=build_system_prompt()), *messages]

    logger.debug("Calling Ollama model with {} messages", len(messages))
    response = _get_model().invoke(messages)
    response = _sanitize_final_answer(response, messages)
    response = _append_sources(response, messages)
    return {"messages": [response]}
