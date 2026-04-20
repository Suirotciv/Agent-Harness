"""Unit tests for argument assertions."""

from __future__ import annotations

import pytest

from agentharness.assertions.argument import (
    assert_arg_lte,
    assert_arg_not_contains,
    assert_arg_pattern,
    assert_arg_schema,
)
from agentharness.mocks.interceptor import ToolCallRecord


def test_assert_arg_lte_ok() -> None:
    recs = [
        ToolCallRecord("issue_refund", {"amount": 50}, "1"),
        ToolCallRecord("issue_refund", {"amount": 100}, "2"),
    ]
    res = assert_arg_lte(recs, tool="issue_refund", arg="amount", value=100)
    assert res.passed is True
    assert res.assertion_name == "assert_arg_lte"
    assert res.regulatory_refs


def test_assert_arg_lte_exceeds() -> None:
    recs = [ToolCallRecord("issue_refund", {"amount": 101}, "1")]
    with pytest.raises(AssertionError, match="exceeds"):
        assert_arg_lte(recs, tool="issue_refund", arg="amount", value=100)


def test_assert_arg_pattern_ok() -> None:
    recs = [ToolCallRecord("x", {"email": "a@b.co"}, "1")]
    res = assert_arg_pattern(recs, tool="x", arg="email", pattern=r".+@.+")
    assert res.passed is True
    assert res.assertion_name == "assert_arg_pattern"
    assert res.regulatory_refs


def test_assert_arg_pattern_invalid_regex() -> None:
    recs = [ToolCallRecord("x", {"email": "a"}, "1")]
    with pytest.raises(ValueError, match="invalid regex"):
        assert_arg_pattern(recs, tool="x", arg="email", pattern="[")


def test_assert_arg_schema_ok() -> None:
    recs = [ToolCallRecord("x", {"amount": 1}, "1")]
    schema = {
        "type": "object",
        "properties": {"amount": {"type": "integer"}},
        "required": ["amount"],
    }
    res = assert_arg_schema(recs, tool="x", schema=schema)
    assert res.passed is True
    assert res.assertion_name == "assert_arg_schema"
    assert res.regulatory_refs


def test_assert_arg_schema_fail() -> None:
    recs = [ToolCallRecord("x", {"amount": "nope"}, "1")]
    schema = {"type": "object", "properties": {"amount": {"type": "integer"}}}
    with pytest.raises(AssertionError, match="schema"):
        assert_arg_schema(recs, tool="x", schema=schema)


def test_assert_arg_not_contains_ok() -> None:
    recs = [ToolCallRecord("x", {"msg": "hello"}, "1")]
    res = assert_arg_not_contains(recs, tool="x", arg="msg", substring="SECRET")
    assert res.passed is True
    assert res.assertion_name == "assert_arg_not_contains"
    assert res.regulatory_refs


def test_assert_arg_not_contains_fail() -> None:
    recs = [ToolCallRecord("x", {"msg": "leak SECRET"}, "1")]
    with pytest.raises(AssertionError, match="forbidden"):
        assert_arg_not_contains(recs, tool="x", arg="msg", substring="SECRET")
