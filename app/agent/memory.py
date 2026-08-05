"""Conversation memory management (short-term + entity/context memory).

This app is a single-user local Streamlit process, so a process-wide
singleton is enough short-term memory: it lets follow-up turns like
"faqat Uzbekistan Airways ko'rsat" or "eng arzonini tanla" resolve against
the *previous* tool result without the LLM re-fetching or re-stating
parameters (the PDF spec's multi-turn requirement).

The LangGraph message history itself (the full turn-by-turn chat) lives in
:class:`app.agent.state.AgentState` — this module only holds the
derived/entity memory that tools need outside of the graph's message list.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.api.schemas import Flight, FlightSearchQuery


@dataclass
class ConversationMemory:
    """Short-term memory: the most recent search result and its parameters."""

    last_query: FlightSearchQuery | None = None
    last_flights: list[Flight] = field(default_factory=list)
    entities: dict[str, str] = field(default_factory=dict)

    def reset(self) -> None:
        self.last_query = None
        self.last_flights = []
        self.entities = {}


_memory = ConversationMemory()


def get_memory() -> ConversationMemory:
    """Return the process-wide :class:`ConversationMemory` singleton."""
    return _memory


def reset_memory() -> None:
    _memory.reset()


def set_last_search(query: FlightSearchQuery, flights: list[Flight]) -> None:
    _memory.last_query = query
    _memory.last_flights = flights
    if query.origin:
        _memory.entities["origin"] = query.origin
    if query.destination:
        _memory.entities["destination"] = query.destination
    if query.departure_date:
        _memory.entities["departure_date"] = query.departure_date


def get_last_flights() -> list[Flight]:
    return list(_memory.last_flights)


def get_last_query() -> FlightSearchQuery | None:
    return _memory.last_query


def remember_entity(key: str, value: str) -> None:
    _memory.entities[key] = value


def get_entity(key: str, default: str | None = None) -> str | None:
    return _memory.entities.get(key, default)
