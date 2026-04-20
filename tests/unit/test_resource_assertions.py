"""Unit tests for resource assertions."""

from __future__ import annotations

import pytest

from agentharness.assertions.resource import assert_cost_under
from agentharness.core.trace import Trace


def test_assert_cost_under_explicit_usd() -> None:
    t = Trace()
    t.attributes["harness.estimated_cost_usd"] = 0.001
    res = assert_cost_under(t, max_usd=0.01)
    assert res.passed is True
    assert res.assertion_name == "assert_cost_under"
    assert res.regulatory_refs


def test_assert_cost_under_exceeds() -> None:
    t = Trace()
    t.attributes["harness.estimated_cost_usd"] = 1.0
    with pytest.raises(AssertionError, match="exceeds max_usd"):
        assert_cost_under(t, max_usd=0.01)


def test_assert_cost_under_unresolvable() -> None:
    t = Trace()
    with pytest.raises(AssertionError, match="could not resolve cost"):
        assert_cost_under(t, max_usd=1.0)


def test_assert_cost_under_tokencost_path() -> None:
    pytest.importorskip("tokencost")
    t = Trace()
    t.attributes["gen_ai.request.model"] = "gpt-4o-mini"
    t.attributes["harness.input_tokens"] = 100
    t.attributes["harness.output_tokens"] = 50
    res = assert_cost_under(t, max_usd=1.0)
    assert res.passed is True
    assert res.assertion_name == "assert_cost_under"
    assert res.regulatory_refs
