"""Statistics page — placeholder. Built out in Milestone 19."""

from __future__ import annotations

from app.ui.components import not_yet_available, render_page_header


def render() -> None:
    render_page_header("Korpus va indeks statistikasi.")
    not_yet_available("Milestone 19")


# See chat.py's comment on this same guard for why it's here.
if __name__ == "__main__":
    render()
