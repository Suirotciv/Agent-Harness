"""Deterministic fault injection.

Injects configurable failures (timeout, HTTP 500, auth error, malformed response)
at specific call indices to test agent recovery behavior. Defaults to
deterministic (call-index-based) mode; seeded random mode is opt-in only.
"""
