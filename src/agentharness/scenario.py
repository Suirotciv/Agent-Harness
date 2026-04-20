"""Scenario decorator for pytest tests (AD-004).

Registered marker: ``agentharness_scenario``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, cast

import pytest

F = TypeVar("F", bound=Callable[..., object])


def scenario(path: str) -> Callable[[F], F]:
    """Mark a test as bound to a scenario file (YAML path relative to project root).

    Use with the ``run`` fixture::

        @scenario("scenarios/refund_happy_path.yaml")
        def test_refund_happy_path(run):
            assert run.trace.attributes.get("harness.scenario_id")
    """

    def _decorate(fn: F) -> F:
        return cast(F, pytest.mark.agentharness_scenario(path=path)(fn))

    return _decorate
