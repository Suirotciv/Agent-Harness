"""Assertion result model (return value for harness assertions)."""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class AssertionResult:
    """Outcome record for a single assertion run (for reporters and compliance context)."""

    passed: bool
    assertion_name: str
    tool: str | None
    message: str
    regulatory_refs: list[str]
    details: dict[str, Any] = field(default_factory=dict)


# Pytest collects finished assertion records from the active test item's stash (see ``finish``).
# Key is shared with ``pytest_plugin`` so hooks can read the same list after each test.
STASH_KEY_ASSERTION_RESULTS: pytest.StashKey[list[AssertionResult]] = pytest.StashKey()

# Flushed by ``pytest_runtest_logreport`` via ``report.nodeid`` (``TestReport`` has no ``.node`` on some pytest versions).
LOGREPORT_PENDING: dict[str, list[AssertionResult]] = {}

# Set only while a test runs (``pytest_plugin`` autouse fixture). Outside pytest, this stays None
# so ``finish()`` does not touch stash — CLI / library callers behave as before.
_pytest_item_ctx: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "agentharness_pytest_item", default=None
)

# Optional list populated by :func:`finish` for consumers that are not pytest (e.g. ``agentharness run``
# CLI). When ``None``, only stash / LOGREPORT_PENDING paths apply (see AD-011, KI-007).
_results_collector: contextvars.ContextVar[list[AssertionResult] | None] = (
    contextvars.ContextVar("agentharness_results_collector", default=None)
)


def set_results_collector(
    lst: list[AssertionResult],
) -> contextvars.Token[list[AssertionResult] | None]:
    """Bind a list to receive every :class:`AssertionResult` from :func:`finish` in this context.

    Returns a token for :func:`reset_results_collector`. Used by the CLI; pytest uses the pytest item
    stash unless this is also set.
    """
    return _results_collector.set(lst)


def reset_results_collector(
    token: contextvars.Token[list[AssertionResult] | None],
) -> None:
    """Restore the previous results collector (end of CLI run or scoped capture)."""
    _results_collector.reset(token)


def bind_pytest_item(item: Any | None) -> contextvars.Token[Any | None]:
    """Bind the executing pytest node for assertion recording. Returns token for :func:`reset_pytest_item`."""
    return _pytest_item_ctx.set(item)


def reset_pytest_item(token: contextvars.Token[Any | None]) -> None:
    """Restore the previous binding (end of test)."""
    _pytest_item_ctx.reset(token)


def _record_result_for_active_pytest_item(result: AssertionResult) -> None:
    """Append to the current item's stash so ``pytest_runtest_logreport`` can recover results after failures.

    Recording happens **before** ``AssertionError`` is raised on failure; otherwise the structured result
    would be lost when pytest captures the exception.
    """
    item = _pytest_item_ctx.get()
    if item is None:
        return
    stash = item.stash
    bucket = stash.get(STASH_KEY_ASSERTION_RESULTS, None)
    if bucket is None:
        bucket = []
        stash[STASH_KEY_ASSERTION_RESULTS] = bucket
    bucket.append(result)
    LOGREPORT_PENDING.setdefault(item.nodeid, []).append(result)


def finish(
    result: AssertionResult, cause: BaseException | None = None
) -> AssertionResult:
    """Return ``result``; if ``passed`` is False, raise ``AssertionError(result.message)`` for pytest.

    When a pytest item is bound (autouse fixture in ``pytest_plugin``), each result is stored on the
    item stash and in ``LOGREPORT_PENDING`` **before** raising, so ``pytest_runtest_makereport`` can
    recover structured outcomes even though the exception consumes the return value on failure.

    When :data:`_results_collector` is set (e.g. ``agentharness run``), ``result`` is appended there
    before any raise, so all assertion modules share this single code path (AD-011).
    """
    bucket = _results_collector.get()
    if bucket is not None:
        bucket.append(result)
    _record_result_for_active_pytest_item(result)
    if not result.passed:
        err = AssertionError(result.message)
        if cause is not None:
            err.__cause__ = cause
        raise err
    return result


# Regulatory mapping (project proposal / compliance traceability)
REFS_ASSERT_CALLED_BEFORE = ["EU AI Act Article 9", "NIST AI RMF TEVV Verify"]
REFS_ASSERT_CALL_COUNT = ["EU AI Act Article 9"]
REFS_ASSERT_COMPLETION = ["EU AI Act Article 9", "NIST AI RMF TEVV Validate"]
REFS_ASSERT_MUTUAL_EXCLUSION = ["EU AI Act Article 9"]
REFS_ASSERT_ARG_LTE = ["EU AI Act Article 15", "Colorado SB 24-205"]
REFS_ASSERT_ARG_PATTERN = ["EU AI Act Article 15"]
REFS_ASSERT_ARG_SCHEMA = ["EU AI Act Article 9", "NIST AI RMF TEVV Verify"]
REFS_ASSERT_ARG_NOT_CONTAINS = ["EU AI Act Article 15", "OWASP LLM06:2025"]
REFS_ASSERT_APPROVAL_GATE = ["EU AI Act Article 14", "Colorado SB 24-205", "OWASP LLM06:2025"]
REFS_ASSERT_NO_LOOP = ["EU AI Act Article 9", "OWASP LLM10:2025"]
REFS_ASSERT_COST_UNDER = ["OWASP LLM10:2025", "EU AI Act Article 9"]
