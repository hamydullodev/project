"""LangGraph agent orchestration layer.

Defines the conversation state, prompts, planner/router logic, graph
nodes, and the compiled StateGraph that ties them together into the
User -> Planner -> LLM -> Router -> Tool -> API -> Formatter -> Memory
-> Final Answer workflow.
"""
