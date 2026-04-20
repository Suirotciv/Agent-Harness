"""Tests for pytest plugin: ``run`` fixture and ``@scenario``."""

from __future__ import annotations

import pytest

from agentharness import scenario
from agentharness.core.runner import run_scenario
from agentharness.telemetry import schema as S


def test_run_scenario_sets_scenario_id() -> None:
    r = run_scenario("scenarios/refund_happy_path.yaml")
    assert r.scenario_path == "scenarios/refund_happy_path.yaml"
    assert r.trace.attributes.get(S.HARNESS_SCENARIO_ID) == "scenarios/refund_happy_path.yaml"


@scenario("scenarios/refund_happy_path.yaml")
def test_run_fixture_injects_result(run):
    assert run.trace.attributes.get(S.HARNESS_SCENARIO_ID) == "scenarios/refund_happy_path.yaml"


def test_run_fixture_without_scenario_marker(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest

        def test_bad(run):
            assert run.trace
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*@scenario*"])
