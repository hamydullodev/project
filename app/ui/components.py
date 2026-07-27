"""
Shared, reusable Streamlit UI components.

WHY THIS MODULE EXISTS
-----------------------
Every page (Home, Chat, Upload, ...) needs the same handful of small UI
fragments — a consistent page header, a connectivity status badge, a
metric card. Defining these once here means every page looks and behaves
consistently, and a visual tweak (e.g. changing how a status badge looks)
happens in one place instead of being copy-pasted across seven page
files.

WHY st.metric/st.container(border=True) INSTEAD OF CUSTOM HTML/CSS
--------------------------------------------------------------------------
Streamlit's native `st.metric` and bordered `st.container` already render
correctly in both light and dark theme (Streamlit's built-in theme
switcher, available from the app's own menu) without any custom CSS to
maintain. Hand-rolled HTML/CSS card components look "prettier" in one
specific theme but very easily look broken in the other (hardcoded
background/text colors that don't adapt) — for a "beautiful UI" that
needs to survive a user's own theme choice, building on Streamlit's own
theme-aware primitives is the more robust choice, not a shortcut.
"""

from __future__ import annotations

import streamlit as st

APP_TITLE = "Oʻzbekiston Qonunchiligi boʻyicha AI Yordamchi"
APP_ICON = "⚖️"


def render_page_header(subtitle: str | None = None) -> None:
    """Consistent title block used at the top of every page."""
    st.title(f"{APP_ICON} {APP_TITLE}")
    if subtitle:
        st.caption(subtitle)


def status_badge(is_ok: bool, ok_label: str, fail_label: str) -> None:
    """A simple success/error status line — used for Ollama/index health checks."""
    if is_ok:
        st.success(f"✅ {ok_label}")
    else:
        st.error(f"❌ {fail_label}")


def not_yet_available(milestone_label: str) -> None:
    """Placeholder shown on pages not yet built, so the full nav shell works today.

    Every page in the spec's required navigation is clickable from
    Milestone 15 onward — pages this milestone doesn't implement show
    this instead of a broken import or a missing page, and get replaced
    with real content in their own milestone.
    """
    st.info(f"🚧 Bu sahifa hali tayyor emas. U **{milestone_label}** bosqichida qoʻshiladi.")
