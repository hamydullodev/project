"""
Central registry of every page in the app, as `st.Page` objects.

WHY THIS MODULE EXISTS
-----------------------
`st.navigation()` (Streamlit's modern multi-page routing API, used
instead of the older filesystem-convention `pages/` auto-discovery
mechanism, for the finer control it gives — custom titles/icons/grouping,
and pages backed by importable, independently testable Python functions
rather than exec'd scripts) needs a list of `st.Page` objects. `st.
page_link()`, used by pages to link to each other (e.g. Home linking to
Chat), needs those SAME `st.Page` OBJECTS, not string paths — a string
path only reliably resolves for the older file-convention approach this
project isn't using.

Defining every page's `st.Page(...)` object exactly once, here, means
every other module that needs to link to a page (`home.py` linking to
`chat.py`) imports the already-constructed object from this one place,
rather than each page re-constructing its own `st.Page` reference to
another page (which would risk two different `st.Page` objects for what
should be the same logical page).

WHY PAGE MODULES IMPORT THIS FILE LAZILY (INSIDE FUNCTIONS)
------------------------------------------------------------------
This module imports every page module's `render` function (to build each
`st.Page(...)`), and some of those page modules (e.g. `home.py`) need to
import THIS module back, to get `st.Page` objects for their own
`st.page_link()` calls — a circular import at module-load time. Each
page's `render()` function defers its `from app.ui.navigation import
...` to inside the function body rather than the top of the file: by the
time `render()` actually executes (invoked from `st.navigation(...).run()`,
which only happens after this module has finished building every page
object), the circular reference is already fully resolved in Python's
module cache, so the deferred import succeeds even though a top-level one
would not.
"""

from __future__ import annotations

import streamlit as st

from app.ui.pages import chat, home, index_management, retrieval_debug, settings, statistics, upload

home_page = st.Page(home.render, title="Bosh sahifa", icon="🏠", url_path="home", default=True)
chat_page = st.Page(chat.render, title="Suhbat", icon="💬", url_path="chat")
upload_page = st.Page(upload.render, title="Hujjat yuklash", icon="📤", url_path="upload")
index_page = st.Page(index_management.render, title="Indeksni boshqarish", icon="🗂️", url_path="index")
debug_page = st.Page(retrieval_debug.render, title="Qidiruv tahlili", icon="🔍", url_path="debug")
stats_page = st.Page(statistics.render, title="Statistika", icon="📊", url_path="stats")
settings_page = st.Page(settings.render, title="Sozlamalar", icon="⚙️", url_path="settings")

PAGES_BY_SECTION = {
    "Asosiy": [home_page],
    "Yordam": [chat_page],
    "Hujjatlar": [upload_page, index_page],
    "Diagnostika": [debug_page, stats_page],
    "Tizim": [settings_page],
}
