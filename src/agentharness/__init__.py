"""AgentHarness -- open-source test harness for AI agents that take real-world actions."""

__version__ = "0.1.0a1"

from agentharness.assertions import (
    AssertionResult,
    assert_approval_gate,
    assert_arg_lte,
    assert_arg_not_contains,
    assert_arg_pattern,
    assert_arg_schema,
    assert_call_count,
    assert_called_before,
    assert_completion,
    assert_cost_under,
    assert_mutual_exclusion,
    assert_no_loop,
)
from agentharness.core.result import RunResult
from agentharness.scenario import scenario

__all__ = [
    "AssertionResult",
    "RunResult",
    "assert_approval_gate",
    "assert_arg_lte",
    "assert_arg_not_contains",
    "assert_arg_pattern",
    "assert_arg_schema",
    "assert_call_count",
    "assert_called_before",
    "assert_completion",
    "assert_cost_under",
    "assert_mutual_exclusion",
    "assert_no_loop",
    "scenario",
]
