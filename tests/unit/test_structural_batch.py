"""Tests for assert_call_count, assert_completion, assert_mutual_exclusion."""

from __future__ import annotations

import pytest

from agentharness.assertions.structural import (
    assert_call_count,
    assert_completion,
    assert_mutual_exclusion,
)
from agentharness.core.trace import Span, Trace, new_span_id, new_trace_id, utc_now_unix_nano
from agentharness.mocks.interceptor import ToolCallRecord
from agentharness.telemetry import schema as S


def test_assert_call_count_ok() -> None:
    res = assert_call_count(["a", "b", "a"], "a", 2)
    assert res.passed is True
    assert res.assertion_name == "assert_call_count"
    assert res.regulatory_refs


def test_assert_call_count_fail() -> None:
    with pytest.raises(AssertionError, match="expected 1 call"):
        assert_call_count(["a", "a"], "a", 1)


def test_assert_mutual_exclusion_ok_single_branch() -> None:
    r1 = assert_mutual_exclusion(["a", "a"], "a", "b")
    assert r1.passed is True
    assert r1.assertion_name == "assert_mutual_exclusion"
    assert r1.regulatory_refs
    r2 = assert_mutual_exclusion(["b"], "a", "b")
    assert r2.passed is True
    assert r2.assertion_name == "assert_mutual_exclusion"
    assert r2.regulatory_refs


def test_assert_mutual_exclusion_fail() -> None:
    with pytest.raises(AssertionError, match="must not both"):
        assert_mutual_exclusion(["a", "b"], "a", "b")


def test_assert_completion_records_ok() -> None:
    res = assert_completion([ToolCallRecord("x", {}, "1")])
    assert res.passed is True
    assert res.assertion_name == "assert_completion"
    assert res.regulatory_refs


def test_assert_completion_records_fail() -> None:
    with pytest.raises(AssertionError, match="assert_completion"):
        assert_completion([ToolCallRecord("x", {}, "1", error="boom")])


def test_assert_completion_trace_ok() -> None:
    tr_id = new_trace_id()
    t = utc_now_unix_nano()
    trace = Trace(
        trace_id=tr_id,
        spans=[
            Span(
                trace_id=tr_id,
                span_id=new_span_id(),
                name="t",
                kind=S.SPAN_KIND_TOOL,
                start_time_unix_nano=t,
                attributes={S.TOOL_NAME: "t"},
                status_code=S.STATUS_OK,
            )
        ],
    )
    res = assert_completion(trace)
    assert res.passed is True
    assert res.assertion_name == "assert_completion"
    assert res.regulatory_refs


def test_assert_completion_trace_error() -> None:
    tr_id = new_trace_id()
    t = utc_now_unix_nano()
    trace = Trace(
        trace_id=tr_id,
        spans=[
            Span(
                trace_id=tr_id,
                span_id=new_span_id(),
                name="t",
                kind=S.SPAN_KIND_TOOL,
                start_time_unix_nano=t,
                attributes={S.TOOL_NAME: "t"},
                status_code=S.STATUS_ERROR,
                status_message="bad",
            )
        ],
    )
    with pytest.raises(AssertionError, match="ERROR status"):
        assert_completion(trace)


def test_assert_call_count_negative_expected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        assert_call_count([], "x", -1)
