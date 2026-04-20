"""Local `run` fixture: LangGraph executor for YAML scenarios with ``steps`` (see ``support/executor``)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_EX_ROOT = Path(__file__).resolve().parent
if str(_EX_ROOT) not in sys.path:
    sys.path.insert(0, str(_EX_ROOT))

from agentharness.core.result import RunResult

from support.executor import run_example_scenario


@pytest.fixture(name="run")
def run_example_for_scenario(request: pytest.FixtureRequest) -> RunResult:
    """Load the scenario path from ``@scenario`` and execute via :func:`run_example_scenario`."""
    marker = request.node.get_closest_marker("agentharness_scenario")
    if marker is None:
        pytest.fail(
            "The `run` fixture requires @scenario(\"path/to/scenario.yaml\") on the test.",
            pytrace=False,
        )
    path = marker.kwargs.get("path")
    if path is None and marker.args:
        path = marker.args[0]
    if path is None:
        pytest.fail(
            "agentharness_scenario marker must include path=...",
            pytrace=False,
        )
    return run_example_scenario(path)
