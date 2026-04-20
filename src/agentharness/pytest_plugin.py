"""Pytest plugin: ``run`` fixture, ``@scenario`` marker (AD-004), AgentHarness terminal reporting."""

from __future__ import annotations

# Assertion capture: :func:`agentharness.assertions.base.finish` records results via the bound pytest
# item's stash and ``LOGREPORT_PENDING`` (``bind_pytest_item`` autouse fixture below). We do **not**
# set :func:`~agentharness.assertions.base.set_results_collector` here — that ContextVar is reserved
# for the ``agentharness run`` CLI so all assertion modules share the single ``finish()`` path
# without per-module monkey-patching (AD-011, KI-007).
from collections.abc import Generator
from typing import Any

import pytest

from agentharness.assertions.base import (
    LOGREPORT_PENDING,
    AssertionResult,
    bind_pytest_item,
    reset_pytest_item,
)
from agentharness.core.result import RunResult
from agentharness.core.runner import run_scenario

# Session stats for ``pytest_terminal_summary``: merged assertion rows (for summary_line counts).
_SESSION_ASSERTION_RESULTS: list[AssertionResult] = []
# Failed assertions to render in the terminal section (excludes expected failures caught by ``pytest.raises``).
_SESSION_FAILURE_PANELS: list[AssertionResult] = []
_CONFIG_ERROR_MESSAGES: list[str] = []


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "agentharness_scenario(path): scenario file path for the agentharness `run` fixture",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    _SESSION_ASSERTION_RESULTS.clear()
    _SESSION_FAILURE_PANELS.clear()
    _CONFIG_ERROR_MESSAGES.clear()
    LOGREPORT_PENDING.clear()


@pytest.fixture(autouse=True)
def _agentharness_bind_item_for_assertions(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Bind the active pytest item so :func:`agentharness.assertions.base.finish` can record results."""
    tok = bind_pytest_item(request.node)
    yield
    reset_pytest_item(tok)


@pytest.fixture
def run(request: pytest.FixtureRequest) -> RunResult:
    """Execute the scenario declared via :func:`agentharness.scenario.scenario` and return ``RunResult``."""
    marker = request.node.get_closest_marker("agentharness_scenario")
    if marker is None:
        pytest.fail(
            'The `run` fixture requires @scenario("path/to/scenario.yaml") on the test.',
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
    return run_scenario(path)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """No-op here: we need the overall call outcome to ignore expected failures (``pytest.raises``).

    Rows are flushed from ``LOGREPORT_PENDING`` in :func:`pytest_runtest_makereport` after the call
    completes so we can correlate with ``rep.passed`` / ``rep.failed``.
    """
    del report  # hook registered for API symmetry; work happens in ``pytest_runtest_makereport``.


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, Any, None]:
    outcome = yield
    rep = outcome.get_result()
    if rep.when != "call":
        return
    excinfo = call.excinfo
    if rep.failed and excinfo is not None and excinfo.type is not None:
        if issubclass(excinfo.type, ValueError):
            _CONFIG_ERROR_MESSAGES.append(str(excinfo.value))
    pending = LOGREPORT_PENDING.pop(item.nodeid, [])
    if not pending:
        return
    test_failed = bool(rep.failed)
    for r in pending:
        if r.passed:
            _SESSION_ASSERTION_RESULTS.append(r)
        elif test_failed:
            _SESSION_ASSERTION_RESULTS.append(r)
    if test_failed:
        _SESSION_FAILURE_PANELS.extend(r for r in pending if not r.passed)


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int, config: pytest.Config
) -> None:
    """Print AgentHarness assertion failures and configuration errors after pytest's own summary."""
    if not _SESSION_ASSERTION_RESULTS and not _CONFIG_ERROR_MESSAGES:
        return

    from agentharness.reporting.console import ConsoleReporter

    if _SESSION_FAILURE_PANELS or _CONFIG_ERROR_MESSAGES:
        terminalreporter.write_sep("=", "AgentHarness")

    cr = ConsoleReporter(_SESSION_FAILURE_PANELS)
    block = cr.render_failures()
    if block.strip():
        for line in block.splitlines():
            terminalreporter.write_line(line)

    for msg in _CONFIG_ERROR_MESSAGES:
        cfg_block = ConsoleReporter.format_configuration_error(ValueError(msg))
        for line in cfg_block.splitlines():
            terminalreporter.write_line(line)

    summary = ConsoleReporter.summary_line(
        _SESSION_ASSERTION_RESULTS,
        configuration_errors=len(_CONFIG_ERROR_MESSAGES),
    )
    terminalreporter.write_line(summary)
