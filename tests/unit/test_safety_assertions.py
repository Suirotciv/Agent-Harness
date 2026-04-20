"""Unit tests for safety assertions."""

from __future__ import annotations

import pytest

from agentharness.assertions.safety import assert_approval_gate, assert_no_loop
from agentharness.mocks.interceptor import ToolCallRecord


def test_assert_approval_gate_ok() -> None:
    recs = [ToolCallRecord("delete_db", {"approved": True, "path": "/tmp"}, "1")]
    res = assert_approval_gate(recs, tool="delete_db")
    assert res.passed is True
    assert res.assertion_name == "assert_approval_gate"
    assert res.regulatory_refs


def test_assert_approval_gate_ok_approval_id() -> None:
    recs = [ToolCallRecord("delete_db", {"approval_id": "a1"}, "1")]
    res = assert_approval_gate(recs, tool="delete_db")
    assert res.passed is True
    assert res.assertion_name == "assert_approval_gate"
    assert res.regulatory_refs


def test_assert_approval_gate_missing() -> None:
    recs = [ToolCallRecord("delete_db", {"path": "/"}, "1")]
    with pytest.raises(AssertionError, match="approval"):
        assert_approval_gate(recs, tool="delete_db")


def test_assert_no_loop_ok() -> None:
    res = assert_no_loop(["a", "a", "b"], tool="a", max_calls=3)
    assert res.passed is True
    assert res.assertion_name == "assert_no_loop"
    assert res.regulatory_refs


def test_assert_no_loop_fail() -> None:
    with pytest.raises(AssertionError, match="exceeds max_calls"):
        assert_no_loop(["x", "x", "x"], tool="x", max_calls=2)
