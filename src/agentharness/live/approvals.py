"""Approval gate with bound artifacts.

Manages human-in-the-loop approval flows. Approval artifacts are
cryptographically tied to tool name, args hash, actor, timestamp,
and run ID to prevent cross-run authorization leakage.
"""
