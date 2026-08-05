"""Streamlit presentation layer.

Contains the visual theme/design tokens (`theme.py`, `styles.py`) and the
reusable UI components (`components/`) that render the agent's state onto
the page. No business logic lives here — components only read from
`st.session_state` and the agent's output, they never call APIs directly.
"""
