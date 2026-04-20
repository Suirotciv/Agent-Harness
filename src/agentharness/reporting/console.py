"""Rich terminal formatting for :class:`~agentharness.assertions.base.AssertionResult`."""

from __future__ import annotations

from collections.abc import Sequence

try:
    from rich.console import Console
    from rich.panel import Panel

    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

from agentharness.assertions.base import AssertionResult

# Snapshot for tests / defensive fallback
RICH_AVAILABLE = _RICH_AVAILABLE


def _plain_block(title: str, body_lines: list[str]) -> str:
    sep = "=" * min(60, max(len(title) + 4, 40))
    lines = [sep, title, sep, *body_lines, sep]
    return "\n".join(lines)


class ConsoleReporter:
    """Format :class:`AssertionResult` lists for terminal output (pytest summary, future CLI)."""

    def __init__(self, results: Sequence[AssertionResult] | None = None) -> None:
        self._results: list[AssertionResult] = list(results or [])

    def render_failures(self) -> str:
        """Return formatted output for **failed** results only; passes yield empty string (silent)."""
        failed = [r for r in self._results if not r.passed]
        if not failed:
            return ""
        parts: list[str] = []
        for r in failed:
            parts.append(self._format_one_failure(r))
        return "\n\n".join(parts)

    def _format_one_failure(self, r: AssertionResult) -> str:
        body_lines = self._failure_body_lines(r)
        title = f"Assertion failed: {r.assertion_name}"
        if _RICH_AVAILABLE:
            try:
                console = Console(color_system="standard", width=100)
                with console.capture() as cap:
                    console.print(
                        Panel("\n".join(body_lines), title=title, border_style="red")
                    )
                return cap.get()
            except Exception:
                pass
        return _plain_block(title, body_lines)

    def _failure_body_lines(self, r: AssertionResult) -> list[str]:
        lines: list[str] = []
        if r.tool:
            lines.append(f"Tool: {r.tool}")
        lines.append(r.message)
        refs = r.regulatory_refs
        if refs:
            lines.append("Regulatory references: " + ", ".join(refs))
        d = r.details
        constraint = d.get("constraint")
        if constraint is not None:
            lines.append(f"constraint: {constraint}")
        for key in ("actual_value", "actual_cost_usd", "ordered_sequence"):
            val = d.get(key)
            if val is not None:
                lines.append(f"{key}: {val!r}")
        return lines

    @staticmethod
    def format_configuration_error(exc: ValueError) -> str:
        """Format a misconfigured test input error (distinct from agent/assertion failure)."""
        msg = str(exc)
        title = "Test configuration error"
        body = msg
        if _RICH_AVAILABLE:
            try:
                console = Console(color_system="standard", width=100)
                with console.capture() as cap:
                    console.print(
                        Panel(
                            body,
                            title=title,
                            border_style="yellow",
                        )
                    )
                return cap.get()
            except Exception:
                pass
        return _plain_block(title, [body])

    @staticmethod
    def summary_line(
        results: Sequence[AssertionResult],
        *,
        configuration_errors: int = 0,
    ) -> str:
        """One-line summary for pytest's terminal section, e.g. ``Agent-Harness: 5 passed, 1 failed``."""
        passed = sum(1 for r in results if r.passed)
        failed_assertions = sum(1 for r in results if not r.passed)
        failed = failed_assertions + configuration_errors
        return f"Agent-Harness: {passed} passed, {failed} failed"
