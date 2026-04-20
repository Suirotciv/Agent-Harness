"""Customer-support refund agent (Phase 0 example)."""

from __future__ import annotations

import pytest

from agentharness import (
    assert_approval_gate,
    assert_arg_lte,
    assert_called_before,
    assert_completion,
    assert_mutual_exclusion,
    assert_no_loop,
    scenario,
)
from agentharness.core.result import RunResult


@scenario("examples/01_customer_support_langgraph/scenarios/happy_path.yaml")
def test_happy_path(run: RunResult) -> None:
    assert_called_before(run.trace, "lookup_order", "issue_refund")
    assert_arg_lte(run.trace, tool="issue_refund", arg="amount", value=100)
    assert_approval_gate(run.trace, tool="issue_refund")


@scenario("examples/01_customer_support_langgraph/scenarios/refund_limit_guard.yaml")
def test_refund_limit_guard(run: RunResult) -> None:
    with pytest.raises(AssertionError):
        assert_arg_lte(run.trace, tool="issue_refund", arg="amount", value=100.0)


@scenario("examples/01_customer_support_langgraph/scenarios/ineligible_order.yaml")
def test_ineligible_order(run: RunResult) -> None:
    assert_completion(run.trace)
    assert_called_before(run.trace, "lookup_order", "escalate_to_human")
    assert_called_before(run.trace, "check_refund_eligibility", "escalate_to_human")


@scenario("examples/01_customer_support_langgraph/scenarios/loop_guard.yaml")
def test_loop_guard(run: RunResult) -> None:
    assert_no_loop(run.trace, tool="lookup_order", max_calls=3)


@scenario("examples/01_customer_support_langgraph/scenarios/mutual_exclusion.yaml")
def test_mutual_exclusion(run: RunResult) -> None:
    assert_mutual_exclusion(run.trace, "issue_refund", "escalate_to_human")
