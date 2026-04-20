"""Cassette read/write -- sanitized recordings of tool responses for deterministic replay.

Handles serialization, PII/secret scrubbing, and keyed lookup by tool name
and normalized argument hash.
"""
