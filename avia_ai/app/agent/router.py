"""Conditional routing logic between LLM tool-call decisions and tool nodes."""

from __future__ import annotations

from typing import Literal

from app.agent.state import AgentState


def route_after_model(state: AgentState) -> Literal["tools", "__end__"]:
    """Send the turn to the tool-execution node if the LLM requested a tool call."""
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return "__end__"
