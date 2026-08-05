"""
Streamlit application entry point.

WHY THIS FILE EXISTS
-----------------------
This is the single script `streamlit run` actually executes (via
`run.py`'s subprocess wrapper — see that file's docstring). It does
exactly two things: configure the page (title, icon, layout — must
happen exactly once, before any other Streamlit call) and hand control
to `st.navigation()`, which renders the sidebar navigation and runs
whichever page the user selected. Every actual page's content lives in
`app/ui/pages/`; this file only wires them together via
`app.ui.navigation`'s registry (see that module's docstring for why the
`st.Page` objects are centralized there rather than built inline here).
"""

from __future__ import annotations

import streamlit as st

from app.ui.components import APP_ICON, APP_TITLE
from app.ui.navigation import PAGES_BY_SECTION

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

navigation = st.navigation(PAGES_BY_SECTION)
navigation.run()
