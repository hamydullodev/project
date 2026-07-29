"""Configuration package.

Exposes a single, already-instantiated `settings` object so the rest of the
app never has to know *how* configuration is loaded — it just does:

    from app.config import settings
    print(settings.embedding_model)
"""

from app.config.settings import Settings, get_settings

settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
