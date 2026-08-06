"""Short-term UI memory: the most recent search's products, chat log, and
the user's in-progress compare selection.

Unlike Avia AI's process-wide ``ConversationMemory`` singleton, this reads
and writes ``st.session_state`` directly: the Streamlit UI here talks to the
agent over HTTP (a separate FastAPI process, possibly serving several
Streamlit sessions), so per-session state is the correct scope — a global
singleton would leak one user's search into another's screen.
"""

from __future__ import annotations

import uuid

import streamlit as st


def init_state() -> None:
    st.session_state.setdefault("thread_id", str(uuid.uuid4()))
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("last_query", "")
    st.session_state.setdefault("last_results", [])
    st.session_state.setdefault("compare_ids", set())
    st.session_state.setdefault("dark_mode", False)


def reset_conversation() -> None:
    st.session_state["thread_id"] = str(uuid.uuid4())
    st.session_state["messages"] = []
    st.session_state["last_query"] = ""
    st.session_state["last_results"] = []
    st.session_state["compare_ids"] = set()


def set_last_search(query: str, results: list[dict]) -> None:
    st.session_state["last_query"] = query
    st.session_state["last_results"] = results


def get_last_results() -> list[dict]:
    return list(st.session_state.get("last_results", []))


def get_last_query() -> str:
    return st.session_state.get("last_query", "")


def has_messages() -> bool:
    return bool(st.session_state.get("messages"))
