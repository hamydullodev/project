"""Query planning node: turns raw user input into a structured intent.

Kept intentionally small: the LLM's tool-calling already does most of the
"which tool with which parameters" reasoning. This node's job is the part a
3B local model is unreliable at — resolving relative dates ("bugun",
"ertaga", "indinga") to absolute ``YYYY-MM-DD`` strings — so the model
always sees an unambiguous date in the prompt instead of having to compute
one itself.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

_RELATIVE_DATES = {
    "bugun": 0,
    "ertaga": 1,
    "indinga": 2,
    "indin": 2,
}

_RELATIVE_RE = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in _RELATIVE_DATES) + r")\b",
    re.IGNORECASE,
)


def resolve_relative_dates(text: str, *, today: date | None = None) -> str:
    """Replace relative date words in ``text`` with absolute ISO dates."""
    reference = today or date.today()

    def _replace(match: re.Match[str]) -> str:
        offset = _RELATIVE_DATES[match.group(1).lower()]
        resolved = reference + timedelta(days=offset)
        return f"{match.group(1)} ({resolved.isoformat()})"

    return _RELATIVE_RE.sub(_replace, text)
