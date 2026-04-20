"""Tests for :mod:`agentharness.telemetry.collector`."""

from __future__ import annotations

import json

from agentharness.mocks.interceptor import ToolCallRecord
from agentharness.telemetry import schema as S
from agentharness.telemetry.collector import TraceCollector


def test_record_populates_span_and_attributes() -> None:
    c = TraceCollector("scn", "mock", seed=None)
    rec = ToolCallRecord(
        tool_name="tool_a",
        args={"x": 1},
        tool_call_id="id-1",
        response={"ok": True},
        error=None,
        duration_ms=2.0,
    )
    c.record(rec)
    span = c.build().spans[0]
    assert span.name == "tool_a"
    assert span.status_code == S.STATUS_OK
    assert span.attributes[S.TOOL_NAME] == "tool_a"
    assert json.loads(span.attributes[S.INPUT_VALUE]) == {"x": 1}
    assert json.loads(span.attributes[S.OUTPUT_VALUE]) == {"ok": True}


def test_build_order_and_idempotent() -> None:
    c = TraceCollector("scn", "mock")
    c.record(
        ToolCallRecord(
            tool_name="first",
            args={},
            tool_call_id="1",
            response="a",
        ),
    )
    c.record(
        ToolCallRecord(
            tool_name="second",
            args={},
            tool_call_id="2",
            response="b",
        ),
    )
    t1 = c.build()
    t2 = c.build()
    assert [s.name for s in t1.spans] == ["first", "second"]
    assert t1 is t2
    assert len(t1.spans) == 2


def test_reset_clears_spans() -> None:
    c = TraceCollector("scn", "mock")
    c.record(ToolCallRecord("t", {}, "1", response="x"))
    assert len(c.build().spans) == 1
    c.reset()
    assert c.build().spans == []


def test_error_record_status_error() -> None:
    c = TraceCollector("scn", "mock")
    c.record(
        ToolCallRecord(
            tool_name="bad",
            args={},
            tool_call_id="1",
            response=None,
            error="boom",
        ),
    )
    span = c.build().spans[0]
    assert span.status_code == S.STATUS_ERROR
    assert span.status_message == "boom"


def test_attribute_keys_are_schema_constants() -> None:
    """Ensure we did not hardcode OpenInference-style strings in tests."""
    c = TraceCollector("scn", "mock")
    c.record(ToolCallRecord("t", {"k": "v"}, "1", response=1))
    span = c.build().spans[0]
    assert S.INPUT_VALUE in span.attributes
    assert S.OUTPUT_VALUE in span.attributes
    assert S.TOOL_NAME in span.attributes
    assert S.OPENINFERENCE_SPAN_KIND in span.attributes
