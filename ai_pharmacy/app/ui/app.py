"""AI Pharmacy — Streamlit application entry point.

Run with:  streamlit run app/ui/app.py
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.database.db import init_db  # noqa: E402
from app.ui.components.sidebar import render_new_search_button  # noqa: E402
from app.ui.components.topbar import render_topbar  # noqa: E402
from app.ui.pages import (  # noqa: E402
    compare_page,
    history_page,
    home_page,
    nearby_page,
    saved_page,
    search_page,
    settings_page,
)
from app.ui.state import init_state  # noqa: E402
from app.ui.styles import inject_custom_css  # noqa: E402

LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo_cropped.png"

st.set_page_config(
    page_title="AI Pharmacy",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
init_state()
inject_custom_css()
render_topbar()

with st.sidebar:
    render_new_search_button()
    st.write("")

pages = [
    st.Page(home_page.render, title="Home", icon="🏠", url_path="home", default=True),
    st.Page(search_page.render, title="Medicine Search", icon="💊", url_path="qidiruv"),
    st.Page(compare_page.render, title="Compare Prices", icon="📊", url_path="taqqoslash"),
    st.Page(nearby_page.render, title="Nearby Pharmacies", icon="📍", url_path="dorixonalar"),
    st.Page(saved_page.render, title="Saved Medicines", icon="❤️", url_path="saqlangan"),
    st.Page(history_page.render, title="History", icon="🕒", url_path="tarix"),
    st.Page(settings_page.render, title="Settings", icon="⚙️", url_path="sozlamalar"),
]
navigation = st.navigation(pages)
navigation.run()
