"""Sozlamalar: dark mode, model info, API key status, guest profile note."""

from __future__ import annotations

import streamlit as st

from app.config import get_settings


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
    st.markdown("#### Model")
    settings = get_settings()
    st.caption(f"Model: `{settings.ollama_model}`")
    st.caption(f"Ollama: `{settings.ollama_base_url}`")

    st.divider()
    st.markdown("#### API holati")
    st.markdown(_status_pill("Reys API", settings.has_flight_provider_credentials), unsafe_allow_html=True)
    st.markdown(_status_pill("Geoapify", settings.has_geoapify_credentials), unsafe_allow_html=True)
    st.markdown(_status_pill("Valyuta kursi", bool(settings.exchange_rate_api_key)), unsafe_allow_html=True)
    st.markdown(_status_pill("Ob-havo", bool(settings.openweather_api_key)), unsafe_allow_html=True)
    st.markdown(_status_pill("Web qidiruv", bool(settings.serper_api_key)), unsafe_allow_html=True)

    if not settings.has_flight_provider_credentials:
        st.warning(
            "Flight Search API key kiritilmagan — reys qidiruv ishlamaydi. "
            ".env fayliga AMADEUS_API_KEY/AMADEUS_API_SECRET qo'shing."
        )

    st.divider()
    st.markdown("#### Profil")
    st.caption("Mehmon foydalanuvchi — bu versiyada autentifikatsiya yo'q.")
