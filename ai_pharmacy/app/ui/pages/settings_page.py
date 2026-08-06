"""Settings: dark mode, model/backend status, disclaimer, reset."""

from __future__ import annotations

import streamlit as st

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.ui.components.hero import DISCLAIMER
from app.ui.state import reset_conversation
from app.ui.utils import API_URL


def _status_pill(label: str, ok: bool) -> str:
    css_class = "status-ok" if ok else "status-bad"
    icon = "✅" if ok else "⚠️"
    return f'<span class="status-pill {css_class}">{icon} {label}</span>'


def render() -> None:
    st.markdown("## ⚙️ Sozlamalar")

    st.markdown("#### Ko'rinish")
    dark = st.session_state.get("dark_mode", False)
    new_dark = st.toggle("Tungi rejim", value=dark)
    if new_dark != dark:
        st.session_state["dark_mode"] = new_dark
        st.rerun()

    st.divider()
    st.markdown("#### Model va backend")
    st.caption(f"Model: `{OLLAMA_MODEL}`")
    st.caption(f"Ollama: `{OLLAMA_BASE_URL}`")
    st.caption(f"Backend: `{API_URL}`")

    ok = True
    try:
        import requests

        ok = requests.get(f"{API_URL}/health", timeout=2).ok
    except Exception:
        ok = False
    st.markdown(_status_pill("Backend ulanishi", ok), unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Suhbat")
    st.caption(f"Suhbat ID: `{st.session_state.thread_id}`")
    if st.button("🔄 Suhbatni tozalash"):
        reset_conversation()
        st.rerun()

    st.divider()
    st.markdown("#### Profil")
    st.caption("Mehmon foydalanuvchi — bu versiyada autentifikatsiya yo'q.")

    st.divider()
    st.markdown(f"<div class='hero-disclaimer'>⚕️ {DISCLAIMER}</div>", unsafe_allow_html=True)
