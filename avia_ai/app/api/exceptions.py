"""Exceptions raised by the API client layer.

Tools catch these and turn them into user-facing, non-technical messages
(see the ``Muhim Eslatma`` / error-handling requirement) instead of letting
raw HTTP/parsing errors reach the LLM or the UI.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for all external-API failures."""


class AuthenticationError(ProviderError):
    """Credentials are missing, invalid, or the provider rejected them."""


class RateLimitError(ProviderError):
    """The provider throttled the request (HTTP 429)."""


class NoResultsError(ProviderError):
    """The request succeeded but returned zero usable results."""


class InvalidRequestError(ProviderError):
    """The request was malformed (bad date, unknown IATA code, etc.)."""


class ProviderUnavailableError(ProviderError):
    """The provider is unreachable, timed out, or returned a 5xx error."""
