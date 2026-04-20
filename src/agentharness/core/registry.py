"""Context-local tool registry (not a global singleton).

Uses context variables to isolate tool registrations per-run, preventing
cross-run contamination in parallel pytest executions.
"""
