"""Upload page — placeholder. Built out in Milestone 17."""

from __future__ import annotations

from app.ui.components import not_yet_available, render_page_header


def render() -> None:
    render_page_header("Yangi hujjatlarni yuklash (PDF, DOCX, TXT, HTML).")
    not_yet_available("Milestone 17")


# See chat.py's comment on this same guard for why it's here.
if __name__ == "__main__":
    render()
