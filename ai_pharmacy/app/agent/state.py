from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Conversation state for the pharmacy price comparison agent.

    Inherits `messages` (with automatic append-reducer) from MessagesState,
    which is what LangGraph's SQLite checkpointer persists per thread_id to
    give the agent conversation memory across turns.
    """
