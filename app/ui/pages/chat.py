"""Chat page — placeholder. Built out in Milestone 16."""

from __future__ import annotations

from app.ui.components import not_yet_available, render_page_header


def render() -> None:
    render_page_header("Savol-javob suhbati.")
    not_yet_available("Milestone 16")


# Lets this file run as a standalone Streamlit script (`streamlit run
# app/ui/pages/chat.py`, or streamlit.testing.v1.AppTest.from_file`),
# where __name__ == "__main__" — while staying a no-op side effect when
# app.ui.navigation imports this module normally to obtain `render` as a
# callable for st.Page(), which is how the real app actually uses it.
if __name__ == "__main__":
    render()
