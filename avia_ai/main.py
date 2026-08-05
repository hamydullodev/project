"""Application entry point.

Run with:  streamlit run main.py
"""

from __future__ import annotations

import streamlit as st

from app.ui.components.sidebar import render_new_chat_button
from app.ui.components.topbar import render_topbar
from app.ui.pages import chat_page, comparison_page, flights_page, settings_page, visa_page
from app.ui.styles import inject_custom_css
from app.utils.logger import configure_logging

st.set_page_config(
    page_title="Avia AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

configure_logging()
inject_custom_css()
render_topbar()

with st.sidebar:
    render_new_chat_button()
    st.write("")

pages = [
    st.Page(chat_page.render, title="Chat", icon="✈️", url_path="chat", default=True),
    st.Page(flights_page.render, title="Reys natijalari", icon="🛫", url_path="reys-natijalari"),
    st.Page(comparison_page.render, title="Taqqoslash", icon="📊", url_path="taqqoslash"),
    st.Page(visa_page.render, title="Viza xizmati", icon="🛂", url_path="viza-xizmati"),
    st.Page(settings_page.render, title="Sozlamalar", icon="⚙️", url_path="sozlamalar"),
]
navigation = st.navigation(pages)
navigation.run()
