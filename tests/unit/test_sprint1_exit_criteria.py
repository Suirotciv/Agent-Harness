"""Sprint 1 exit criteria evidence (PROJECT_CONTEXT.md)."""

from __future__ import annotations

from agentharness import assert_called_before, scenario


@scenario("scenarios/refund_happy_path.yaml")
def test_lookup_called_before_refund(run):
    assert_called_before(run.trace, "lookup_order", "issue_refund")
