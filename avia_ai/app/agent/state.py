"""LangGraph conversation state schema.

A single ``messages`` channel is enough here: tool-call results and the
short-term entity/flight memory (:mod:`app.agent.memory`) already carry the
rest of what follow-up turns need, so the graph state itself stays minimal
and lets LangGraph's checkpointer persist just the chat history.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """The graph's per-thread state, persisted by the checkpointer."""

    messages: Annotated[list, add_messages]
