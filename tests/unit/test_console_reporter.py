"""Unit tests for ``ConsoleReporter``."""

from __future__ import annotations

import pytest

from agentharness.assertions.base import AssertionResult
from agentharness.reporting import console as console_mod


def _result(
    *,
    passed: bool,
    name: str = "assert_x",
    tool: str | None = None,
    message: str = "msg",
    regulatory_refs: list[str] | None = None,
    details: dict | None = None,
) -> AssertionResult:
    return AssertionResult(
        passed=passed,
        assertion_name=name,
        tool=tool,
        message=message,
        regulatory_refs=regulatory_refs or ["EU AI Act Article 9"],
        details=details or {},
    )


def test_passing_results_silent() -> None:
    r = _result(passed=True)
    cr = console_mod.ConsoleReporter([r])
    assert cr.render_failures().strip() == ""


def test_failing_result_contains_fields() -> None:
    r = _result(
        passed=False,
        name="assert_called_before",
        message="order wrong",
        regulatory_refs=["EU AI Act Article 9", "NIST AI RMF TEVV Verify"],
        details={"constraint": "earlier before later", "ordered_sequence": ["b", "a"]},
    )
    out = console_mod.ConsoleReporter([r]).render_failures()
    assert "assert_called_before" in out
    assert "order wrong" in out
    assert "EU AI Act Article 9" in out


def test_configuration_error_label() -> None:
    block = console_mod.ConsoleReporter.format_configuration_error(
        ValueError("assert_arg_pattern: invalid regex: bad")
    )
    assert "Test configuration error" in block or "configuration error" in block.lower()
    assert "invalid regex" in block


def test_summary_line_mixed() -> None:
    a = _result(passed=True)
    b = _result(passed=False, message="m")
    s = console_mod.ConsoleReporter.summary_line([a, b], configuration_errors=0)
    assert s == "AgentHarness: 1 passed, 1 failed"
    s2 = console_mod.ConsoleReporter.summary_line([], configuration_errors=2)
    assert "2 failed" in s2
    assert "0 passed" in s2


def test_details_missing_keys_safe() -> None:
    r = AssertionResult(
        passed=False,
        assertion_name="n",
        tool=None,
        message="m",
        regulatory_refs=[],
        details={},
    )
    out = console_mod.ConsoleReporter([r]).render_failures()
    assert "m" in out
    assert "Assertion failed" in out


def test_rich_unavailable_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(console_mod, "_RICH_AVAILABLE", False)
    r = _result(passed=False, message="boom")
    out = console_mod.ConsoleReporter([r]).render_failures()
    assert "boom" in out
    assert "=" in out

