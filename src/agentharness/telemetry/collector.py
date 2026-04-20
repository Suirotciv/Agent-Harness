"""TraceCollector: convert :class:`~agentharness.mocks.interceptor.ToolCallRecord` into tool spans.

Import from :mod:`agentharness.telemetry.collector` directly — this module is **not** re-exported
from :mod:`agentharness.telemetry` (same pattern as :mod:`agentharness.telemetry.jsonl`: package
``__init__`` stays free of imports that pull in :class:`~agentharness.core.trace.Trace` in ways
that complicate circular dependencies).
"""

from __future__ import annotations

import json
from typing import cast

from agentharness.core.trace import (
    Span,
    SpanStatusCode,
    Trace,
    new_span_id,
    utc_now_unix_nano,
)
from agentharness.mocks.interceptor import ToolCallRecord
from agentharness.telemetry import schema as S


class TraceCollector:
    """Accumulate ``ToolCallRecord`` rows as OpenInference-aligned TOOL spans on one trace."""

    def __init__(
        self,
        scenario_id: str,
        mode: str,
        seed: int | None = None,
    ) -> None:
        self._trace = Trace()
        self._trace.attributes[S.HARNESS_SCENARIO_ID] = scenario_id
        self._trace.attributes[S.HARNESS_MODE] = mode
        if seed is not None:
            self._trace.attributes[S.HARNESS_SEED] = seed

    def record(self, tool_call_record: ToolCallRecord) -> None:
        """Append a span derived from ``tool_call_record`` (insertion order)."""
        rec = tool_call_record
        now = utc_now_unix_nano()
        if rec.duration_ms is not None:
            end_ns = now
            start_ns = max(0, end_ns - int(rec.duration_ms * 1_000_000))
        else:
            start_ns = end_ns = now

        ok = rec.error is None
        status = cast(
            SpanStatusCode,
            S.STATUS_OK if ok else S.STATUS_ERROR,
        )
        span = Span(
            trace_id=self._trace.trace_id,
            span_id=new_span_id(),
            name=rec.tool_name,
            kind=S.SPAN_KIND_TOOL,
            start_time_unix_nano=start_ns,
            end_time_unix_nano=end_ns,
            status_code=status,
            status_message=rec.error,
            attributes={
                S.OPENINFERENCE_SPAN_KIND: S.SPAN_KIND_TOOL,
                S.TOOL_NAME: rec.tool_name,
                S.INPUT_VALUE: json.dumps(rec.args, sort_keys=True, default=str),
                S.OUTPUT_VALUE: json.dumps(rec.response, default=str),
            },
        )
        self._trace.add_span(span)

    def build(self) -> Trace:
        """Return the current trace (non-destructive; same object on repeated calls)."""
        return self._trace

    def reset(self) -> None:
        """Clear recorded spans so this collector can be reused."""
        self._trace.spans.clear()
