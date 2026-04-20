"""Telemetry module -- trace collection, schema definitions, and export to external backends.

JSONL helpers live in :mod:`agentharness.telemetry.jsonl` and are **not** re-exported here:
importing them from this package's ``__init__`` would create a circular import with
:class:`~agentharness.core.trace.Trace` (``core.trace`` loads ``telemetry`` while ``jsonl`` needs ``Trace``).

:class:`~agentharness.telemetry.collector.TraceCollector` must be imported from
:mod:`agentharness.telemetry.collector` directly for the same reason.
"""
