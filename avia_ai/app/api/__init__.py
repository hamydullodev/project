"""External API integration layer.

Contains the typed data-provider clients (e.g. Amadeus) and the Pydantic
schemas describing the data they return. This is the ONLY layer in the
codebase allowed to perform network I/O against flight/currency/weather
providers — tools call into this layer, never `requests` directly.
"""
