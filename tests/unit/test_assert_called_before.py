"""Unit tests for assert_called_before."""

from __future__ import annotations

import pytest

from agentharness.assertions.structural import assert_called_before
from agentharness.core.trace import Span, Trace, new_span_id, new_trace_id, utc_now_unix_nano
from agentharness.mocks.interceptor import HarnessInterceptor, InterceptMode, ToolCallRecord
from agentharness.telemetry import schema as S


def _tool_span(trace_id: str, name: str, t0: int) -> Span:
    sid = new_span_id()
    return Span(
        trace_id=trace_id,
        span_id=sid,
        name=name,
        kind=S.SPAN_KIND_TOOL,
        start_time_unix_nano=t0,
        end_time_unix_nano=t0 + 100,
        attributes={
            S.OPENINFERENCE_SPAN_KIND: S.SPAN_KIND_TOOL,
            S.TOOL_NAME: name,
        },
    )


def test_assert_called_before_trace_ok() -> None:
    tr_id = new_trace_id()
    t0 = utc_now_unix_nano()
    trace = Trace(
        trace_id=tr_id,
        spans=[
            _tool_span(tr_id, "lookup_order", t0),
            _tool_span(tr_id, "issue_refund", t0 + 1_000),
        ],
    )
    res = assert_called_before(trace, "lookup_order", "issue_refund")
    assert res.passed is True
    assert res.assertion_name == "assert_called_before"
    assert res.regulatory_refs


def test_assert_called_before_trace_wrong_order() -> None:
    tr_id = new_trace_id()
    t0 = utc_now_unix_nano()
    trace = Trace(
        trace_id=tr_id,
        spans=[
            _tool_span(tr_id, "issue_refund", t0),
            _tool_span(tr_id, "lookup_order", t0 + 1_000),
        ],
    )
    with pytest.raises(AssertionError, match=r"expected 'lookup_order' before 'issue_refund'"):
        assert_called_before(trace, "lookup_order", "issue_refund")


def test_assert_called_before_missing_earlier() -> None:
    tr_id = new_trace_id()
    trace = Trace(
        trace_id=tr_id,
        spans=[_tool_span(tr_id, "issue_refund", utc_now_unix_nano())],
    )
    with pytest.raises(AssertionError, match=r"'lookup_order' was never called"):
        assert_called_before(trace, "lookup_order", "issue_refund")


def test_assert_called_before_missing_later() -> None:
    tr_id = new_trace_id()
    trace = Trace(
        trace_id=tr_id,
        spans=[_tool_span(tr_id, "lookup_order", utc_now_unix_nano())],
    )
    with pytest.raises(AssertionError, match=r"'issue_refund' was never called"):
        assert_called_before(trace, "lookup_order", "issue_refund")


def test_assert_called_before_string_sequence() -> None:
    res = assert_called_before(["lookup_order", "issue_refund"], "lookup_order", "issue_refund")
    assert res.passed is True
    assert res.assertion_name == "assert_called_before"
    assert res.regulatory_refs


def test_assert_called_before_tool_records() -> None:
    recs = [
        ToolCallRecord("lookup_order", {}, "1"),
        ToolCallRecord("issue_refund", {}, "2"),
    ]
    res = assert_called_before(recs, "lookup_order", "issue_refund")
    assert res.passed is True
    assert res.assertion_name == "assert_called_before"
    assert res.regulatory_refs


def test_assert_called_before_interceptor_calls() -> None:
    h = HarnessInterceptor(
        mode=InterceptMode.MOCK,
        mock_responses={"lookup_order": 1, "issue_refund": 2},
    )
    h.intercept_sync("lookup_order", {}, "x", execute_real=None)
    h.intercept_sync("issue_refund", {}, "y", execute_real=None)
    res = assert_called_before(h.calls, "lookup_order", "issue_refund")
    assert res.passed is True
    assert res.assertion_name == "assert_called_before"
    assert res.regulatory_refs


def test_assert_called_before_rejects_bare_str() -> None:
    with pytest.raises(TypeError, match="not str"):
        assert_called_before("lookup_order", "lookup_order", "issue_refund")  # type: ignore[arg-type]
