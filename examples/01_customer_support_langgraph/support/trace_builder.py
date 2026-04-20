"""Build :class:`~agentharness.core.trace.Trace` from recorded tool calls (Phase 0 example)."""

from __future__ import annotations

import json

from agentharness.core.trace import Span, Trace, new_span_id, utc_now_unix_nano
from agentharness.mocks.interceptor import ToolCallRecord
from agentharness.telemetry import schema as S


def tool_records_to_trace(
    records: list[ToolCallRecord],
    *,
    scenario_id: str,
) -> Trace:
    """Turn :class:`ToolCallRecord` rows into a trace with ``input.value`` JSON args per AD-003."""
    trace = Trace()
    trace.attributes[S.HARNESS_SCENARIO_ID] = scenario_id
    t0 = utc_now_unix_nano()
    for i, rec in enumerate(records):
        start = t0 + i * 1_000_000
        span = Span(
            trace_id=trace.trace_id,
            span_id=new_span_id(),
            name=rec.tool_name,
            kind=S.SPAN_KIND_TOOL,
            start_time_unix_nano=start,
            end_time_unix_nano=start + 500_000,
            attributes={
                S.OPENINFERENCE_SPAN_KIND: S.SPAN_KIND_TOOL,
                S.TOOL_NAME: rec.tool_name,
                S.INPUT_VALUE: json.dumps(rec.args, sort_keys=True),
            },
            status_code=S.STATUS_ERROR if rec.error else S.STATUS_OK,
            status_message=rec.error,
        )
        trace.add_span(span)
    return trace
