"""Injected custom CSS: the "Avia AI" design system.

Light-by-default, premium travel-platform look (rounded corners, soft
shadows, subtle glass, smooth hover/fade animations). The light/dark toggle
is done server-side: :func:`inject_custom_css` takes the current
``dark_mode`` flag from session state and emits the matching color values
directly, re-injecting on every rerun — no client-side JS/localStorage
needed since Streamlit already reruns the whole script on interaction.
"""

from __future__ import annotations

import streamlit as st

from app.ui import theme


def inject_custom_css() -> None:
    """Inject the app's custom CSS, honoring the session's dark-mode flag."""
    dark = st.session_state.get("dark_mode", False)

    bg = theme.BACKGROUND_DARK if dark else theme.BACKGROUND
    surface = theme.SURFACE_DARK if dark else theme.SURFACE
    surface_alt = theme.SURFACE_ALT_DARK if dark else theme.SURFACE_ALT
    border = theme.BORDER_DARK if dark else theme.BORDER
    text_primary = theme.TEXT_PRIMARY_DARK if dark else theme.TEXT_PRIMARY
    text_muted = theme.TEXT_MUTED_DARK if dark else theme.TEXT_MUTED

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {{
            --bg: {bg};
            --surface: {surface};
            --surface-alt: {surface_alt};
            --border: {border};
            --text-primary: {text_primary};
            --text-muted: {text_muted};
        }}

        html, body, [class*="css"] {{
            font-family: {theme.FONT_STACK};
        }}

        .stApp {{
            background: {bg};
            color: {text_primary};
        }}
        [data-testid="stSidebar"] {{
            background: {surface};
            border-right: 1px solid {border};
        }}
        [data-testid="stHeader"] {{
            background: transparent;
        }}
        [data-testid="stChatInput"] {{
            border-radius: {theme.RADIUS_LG};
        }}
        button[kind] {{
            border-radius: {theme.RADIUS_SM} !important;
            transition: transform 0.12s ease, box-shadow 0.12s ease !important;
        }}
        button[kind]:hover {{
            transform: translateY(-1px);
            box-shadow: {theme.SHADOW_SM};
        }}
        button[kind]:active {{
            transform: translateY(0px) scale(0.98);
        }}

        /* --- Brand --- */
        .avia-logo {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: {theme.ACCENT_GRADIENT};
            font-size: 1.1rem;
            box-shadow: {theme.SHADOW_SM};
        }}
        .gradient-text {{
            background: {theme.ACCENT_GRADIENT};
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }}

        /* --- Cards --- */
        .glass-card {{
            background: {surface};
            border: 1px solid {border};
            border-radius: {theme.RADIUS_MD};
            padding: {theme.SPACE_MD};
            margin-bottom: {theme.SPACE_SM};
            box-shadow: {theme.SHADOW_SM};
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }}
        .glass-card:hover {{
            transform: translateY(-3px);
            box-shadow: {theme.SHADOW_MD};
            border-color: {theme.PRIMARY};
        }}
        /* --- Hero --- */
        .hero-wrap {{
            text-align: center;
            padding: 4rem 1rem 2.5rem 1rem;
        }}
        .hero-icon {{
            font-size: 3.2rem;
            margin-bottom: 1rem;
        }}
        .hero-title {{
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 0.5rem;
        }}
        .hero-subtitle {{
            font-size: 1.05rem;
            color: {text_muted};
        }}

        /* --- Chat bubbles (ChatGPT-style: user = bubble, assistant = plain) --- */
        .bubble-row {{
            display: flex;
            margin-bottom: 1.1rem;
            animation: fadeIn 0.3s ease;
        }}
        .bubble-row.user {{ justify-content: flex-end; }}
        .bubble-row.assistant {{ justify-content: flex-start; }}
        .bubble {{
            max-width: 80%;
            line-height: 1.6;
        }}
        .bubble.user {{
            background: {theme.ACCENT_GRADIENT};
            color: white;
            padding: 0.65rem 1rem;
            border-radius: {theme.RADIUS_MD};
            border-bottom-right-radius: 4px;
        }}
        .bubble.assistant {{
            background: transparent;
            border: none;
            box-shadow: none;
            padding: 0;
            max-width: 92%;
        }}
        .bubble table {{
            font-size: 0.85rem;
            border-collapse: collapse;
            width: 100%;
            margin: 0.5rem 0;
        }}
        .bubble th, .bubble td {{
            border: 1px solid {border};
            padding: 4px 8px;
            text-align: left;
        }}
        .bubble pre {{
            background: {surface_alt};
            border: 1px solid {border};
            border-radius: {theme.RADIUS_SM};
            padding: 0.75rem 1rem;
            overflow-x: auto;
        }}
        .bubble code {{
            background: {surface_alt};
            border-radius: 4px;
            padding: 1px 5px;
            font-size: 0.9em;
        }}
        .bubble pre code {{ background: transparent; padding: 0; }}
        .bubble p:first-child {{ margin-top: 0; }}
        .bubble p:last-child {{ margin-bottom: 0; }}

        /* --- Status pills --- */
        .status-pill {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .status-ok {{ background: rgba(16, 185, 129, 0.12); color: {theme.SUCCESS}; }}
        .status-bad {{ background: rgba(239, 68, 68, 0.12); color: {theme.DANGER}; }}

        /* --- Notification / error card --- */
        .notice-card {{
            display: flex;
            gap: 0.6rem;
            align-items: flex-start;
            background: {surface};
            border: 1px solid {border};
            border-left: 4px solid {theme.DANGER};
            border-radius: {theme.RADIUS_SM};
            padding: 0.8rem 1rem;
            margin: 0.5rem 0;
        }}
        .notice-card.info {{ border-left-color: {theme.PRIMARY}; }}
        .notice-card .notice-title {{ font-weight: 700; margin-bottom: 2px; }}
        .notice-card .notice-body {{ color: {text_muted}; font-size: 0.92rem; }}

        /* --- Typing indicator --- */
        .typing-dots span {{
            display: inline-block;
            width: 6px;
            height: 6px;
            margin-right: 3px;
            border-radius: 50%;
            background: {text_muted};
            animation: blink 1.2s infinite ease-in-out;
        }}
        .typing-dots span:nth-child(2) {{ animation-delay: 0.2s; }}
        .typing-dots span:nth-child(3) {{ animation-delay: 0.4s; }}
        @keyframes blink {{
            0%, 80%, 100% {{ opacity: 0.2; }}
            40% {{ opacity: 1; }}
        }}
        .fade-in {{ animation: fadeIn 0.35s ease; }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
