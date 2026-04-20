"""Tiered emergency stop controller (SOFT/HARD/ABORT).

Orchestrates agent interruption at three tiers with explicit latency
guarantees: orchestrator-level (<500ms), cooperative (<3s), and
best-effort for in-flight calls.
"""
