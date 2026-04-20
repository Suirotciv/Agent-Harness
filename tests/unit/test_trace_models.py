"""Unit tests for Trace and Span pydantic models."""

from __future__ import annotations

import json

import pytest

from agentharness.core.trace import (
    Span,
    Trace,
    new_span_id,
    new_trace_id,
    utc_now_unix_nano,
)
from agentharness.telemetry import schema as S


def test_new_ids_format() -> None:
    tid = new_trace_id()
    sid = new_span_id()
    assert len(tid) == 32 and int(tid, 16) >= 0
    assert len(sid) == 16 and int(sid, 16) >= 0


def test_trace_add_span_validates_trace_id() -> None:
    tr = Trace()
    other = new_trace_id()
    sp = Span(
        trace_id=other,
        span_id=new_span_id(),
        name="tool",
        kind=S.SPAN_KIND_TOOL,
        start_time_unix_nano=utc_now_unix_nano(),
    )
    with pytest.raises(ValueError, match="trace_id"):
        tr.add_span(sp)


def test_trace_constructor_validates_span_trace_ids() -> None:
    tr_id = new_trace_id()
    bad = Span(
        trace_id=new_trace_id(),
        span_id=new_span_id(),
        name="x",
        start_time_unix_nano=1,
    )
    with pytest.raises(ValueError, match=r"spans\[0\]"):
        Trace(trace_id=tr_id, spans=[bad])


def test_trace_json_roundtrip() -> None:
    tr_id = new_trace_id()
    parent = new_span_id()
    child = new_span_id()
    t0 = 1_700_000_000_000_000_000
    trace = Trace(
        trace_id=tr_id,
        attributes={
            S.HARNESS_SCENARIO_ID: "refund_happy_path",
            S.HARNESS_MODE: "mock",
            S.GEN_AI_SYSTEM: "langgraph",
        },
        spans=[
            Span(
                trace_id=tr_id,
                span_id=parent,
                parent_span_id=None,
                name="agent",
                kind=S.SPAN_KIND_AGENT,
                start_time_unix_nano=t0,
                end_time_unix_nano=t0 + 1_000,
                status_code=S.STATUS_OK,
                attributes={S.OPENINFERENCE_SPAN_KIND: S.SPAN_KIND_AGENT},
            ),
            Span(
                trace_id=tr_id,
                span_id=child,
                parent_span_id=parent,
                name="lookup_order",
                kind=S.SPAN_KIND_TOOL,
                start_time_unix_nano=t0 + 500,
                end_time_unix_nano=t0 + 800,
                attributes={
                    S.OPENINFERENCE_SPAN_KIND: S.SPAN_KIND_TOOL,
                    S.TOOL_NAME: "lookup_order",
                },
            ),
        ],
    )
    dumped = trace.model_dump(mode="json")
    raw = json.dumps(dumped)
    restored = Trace.model_validate_json(raw)
    assert restored.trace_id == tr_id
    assert len(restored.spans) == 2
    assert restored.spans[1].parent_span_id == parent


def test_extra_attributes_allowed() -> None:
    tr = Trace(harness_custom_field=123)  # type: ignore[call-arg]
    assert tr.model_extra == {"harness_custom_field": 123}
