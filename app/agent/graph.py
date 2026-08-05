"""Compiled LangGraph StateGraph wiring all agent nodes together.

A minimal ReAct-style loop: ``agent`` (LLM decides / responds) <-> ``tools``
(executes whichever tool the LLM called), looping until the LLM answers
without a tool call. An in-memory checkpointer keys state by ``thread_id``
so the Streamlit session's chat history persists across turns without the
agent "starting from scratch" (the PDF spec's multi-turn requirement).
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.nodes import call_model
from app.agent.router import route_after_model
from app.agent.state import AgentState
from app.tools import ALL_TOOLS

_checkpointer = MemorySaver()
_graph = None


def build_graph():
    """Build and compile the agent's :class:`StateGraph`."""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", route_after_model, {"tools": "tools", "__end__": END})
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=_checkpointer)


def get_graph():
    """Return a process-wide compiled graph singleton."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
