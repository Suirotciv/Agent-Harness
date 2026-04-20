"""Structural assertions (Tests 1.1-1.4).

assert_called_before, assert_call_count, assert_completion, assert_mutual_exclusion.
Verifies the agent took the right actions in the right order.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeGuard

from agentharness.assertions.base import (
    REFS_ASSERT_CALLED_BEFORE,
    REFS_ASSERT_CALL_COUNT,
    REFS_ASSERT_COMPLETION,
    REFS_ASSERT_MUTUAL_EXCLUSION,
    AssertionResult,
    finish,
)
from agentharness.core.trace import Span, Trace
from agentharness.mocks.interceptor import ToolCallRecord
from agentharness.telemetry import schema as S


def _is_tool_record_sequence(
    seq: Sequence[ToolCallRecord] | Sequence[str],
) -> TypeGuard[Sequence[ToolCallRecord]]:
    if not seq:
        return False
    return isinstance(seq[0], ToolCallRecord)


def _ordered_tool_names(
    trace_or_calls: Trace | Sequence[ToolCallRecord] | Sequence[str],
) -> list[str]:
    """Flatten trace or call records into tool names in invocation order."""
    if isinstance(trace_or_calls, Trace):
        return _tool_names_from_trace(trace_or_calls)
    if isinstance(trace_or_calls, (str, bytes)):
        msg = "assert_called_before expected Trace or a sequence of tool calls, not str/bytes"
        raise TypeError(msg)
    if not trace_or_calls:
        return []
    if _is_tool_record_sequence(trace_or_calls):
        return [r.tool_name for r in trace_or_calls]
    return [str(x) for x in trace_or_calls]


def _span_tool_name(span: Span) -> str | None:
    """Return the logical tool name for a span, or None if not a tool call."""
    attrs = span.attributes
    explicit = attrs.get(S.TOOL_NAME)
    if explicit is not None and str(explicit).strip() != "":
        return str(explicit)
    is_tool = (
        span.kind == S.SPAN_KIND_TOOL
        or attrs.get(S.OPENINFERENCE_SPAN_KIND) == S.SPAN_KIND_TOOL
    )
    if is_tool and span.name:
        return span.name
    return None


def _tool_names_from_trace(trace: Trace) -> list[str]:
    names: list[str] = []
    for span in trace.spans:
        tn = _span_tool_name(span)
        if tn is not None:
            names.append(tn)
    return names


def _first_index(names: list[str], tool: str) -> int | None:
    try:
        return names.index(tool)
    except ValueError:
        return None


def assert_called_before(
    trace_or_calls: Trace | Sequence[ToolCallRecord] | Sequence[str],
    earlier_tool: str,
    later_tool: str,
) -> AssertionResult:
    """Assert ``earlier_tool`` is invoked at least once before the first ``later_tool``.

    Ordering follows:

    * ``Trace``: tool spans in ``trace.spans`` order (``tool.name`` or TOOL-kind + span name).
    * ``Sequence[ToolCallRecord]``: ``calls`` list order from the interceptor.
    * ``Sequence[str]``: explicit tool names in call order (useful in unit tests).

    The check uses the **first** occurrence of each name: the first index of
    ``earlier_tool`` must be strictly less than the first index of ``later_tool``.

    Raises:
        AssertionError: If ordering is violated or either tool never appears.
        TypeError: If ``trace_or_calls`` is a bare string (common mistake).
    """
    ordered = _ordered_tool_names(trace_or_calls)
    idx_early = _first_index(ordered, earlier_tool)
    idx_late = _first_index(ordered, later_tool)

    if idx_early is None:
        msg = (
            f"assert_called_before: tool {earlier_tool!r} was never called. "
            f"Order seen: {ordered!r}"
        )
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_called_before",
                tool=None,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_CALLED_BEFORE),
                details={
                    "earlier_tool": earlier_tool,
                    "later_tool": later_tool,
                    "ordered_sequence": ordered,
                    "constraint": "first occurrence of earlier_tool must be before first occurrence of later_tool",
                },
            )
        )
    if idx_late is None:
        msg = (
            f"assert_called_before: tool {later_tool!r} was never called. "
            f"Order seen: {ordered!r}"
        )
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_called_before",
                tool=None,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_CALLED_BEFORE),
                details={
                    "earlier_tool": earlier_tool,
                    "later_tool": later_tool,
                    "ordered_sequence": ordered,
                    "constraint": "first occurrence of earlier_tool must be before first occurrence of later_tool",
                },
            )
        )
    if idx_early >= idx_late:
        msg = (
            f"assert_called_before: expected {earlier_tool!r} before {later_tool!r}, "
            f"but first {later_tool!r} is at index {idx_late} and first "
            f"{earlier_tool!r} is at index {idx_early}. Full order: {ordered!r}"
        )
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_called_before",
                tool=None,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_CALLED_BEFORE),
                details={
                    "earlier_tool": earlier_tool,
                    "later_tool": later_tool,
                    "ordered_sequence": ordered,
                    "idx_earlier": idx_early,
                    "idx_later": idx_late,
                    "constraint": "first occurrence of earlier_tool must be before first occurrence of later_tool",
                },
            )
        )

    ok_msg = (
        f"assert_called_before passed: first {earlier_tool!r} at index {idx_early} before "
        f"first {later_tool!r} at index {idx_late}. order={ordered!r}"
    )
    return finish(
        AssertionResult(
            passed=True,
            assertion_name="assert_called_before",
            tool=None,
            message=ok_msg,
            regulatory_refs=list(REFS_ASSERT_CALLED_BEFORE),
            details={
                "earlier_tool": earlier_tool,
                "later_tool": later_tool,
                "ordered_sequence": ordered,
                "idx_earlier": idx_early,
                "idx_later": idx_late,
                "constraint": "first occurrence of earlier_tool must be before first occurrence of later_tool",
            },
        )
    )


def assert_call_count(
    trace_or_calls: Trace | Sequence[ToolCallRecord] | Sequence[str],
    tool: str,
    expected: int,
) -> AssertionResult:
    """Assert ``tool`` appears exactly ``expected`` times in the tool-call sequence.

    Same sources as :func:`assert_called_before` (trace spans, records, or name list).
    ``expected`` must be non-negative.
    """
    if expected < 0:
        raise ValueError("assert_call_count: expected must be non-negative")
    ordered = _ordered_tool_names(trace_or_calls)
    actual = ordered.count(tool)
    if actual != expected:
        msg = (
            f"assert_call_count: expected {expected} call(s) to {tool!r}, "
            f"got {actual}. Full order: {ordered!r}"
        )
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_call_count",
                tool=tool,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_CALL_COUNT),
                details={
                    "tool": tool,
                    "expected": expected,
                    "actual": actual,
                    "ordered_sequence": ordered,
                    "constraint": "observed call count for tool must equal expected",
                },
            )
        )
    ok_msg = (
        f"assert_call_count passed: tool {tool!r} called exactly {expected} time(s). "
        f"order={ordered!r}"
    )
    return finish(
        AssertionResult(
            passed=True,
            assertion_name="assert_call_count",
            tool=tool,
            message=ok_msg,
            regulatory_refs=list(REFS_ASSERT_CALL_COUNT),
            details={
                "tool": tool,
                "expected": expected,
                "actual": actual,
                "ordered_sequence": ordered,
                "constraint": "observed call count for tool must equal expected",
            },
        )
    )


def assert_completion(trace_or_calls: Trace | Sequence[ToolCallRecord]) -> AssertionResult:
    """Assert there are no failed tool calls (errors) in the trace or records.

    * ``Trace``: every span that represents a tool call must not have
      ``status_code == ERROR``.
    * ``Sequence[ToolCallRecord]``: every record must have ``error is None``.

    Spans that are not tool calls are ignored. Vacuously passes if there are no
    tool spans or no records.

    Cannot be used with a bare ``Sequence[str]`` — there is no error metadata.
    """
    if isinstance(trace_or_calls, Trace):
        for span in trace_or_calls.spans:
            if _span_tool_name(span) is None:
                continue
            if span.status_code == S.STATUS_ERROR:
                status_msg = span.status_message or "no message"
                msg = (
                    f"assert_completion: tool span {span.name!r} has ERROR status: {status_msg}"
                )
                return finish(
                    AssertionResult(
                        passed=False,
                        assertion_name="assert_completion",
                        tool=_span_tool_name(span),
                        message=msg,
                        regulatory_refs=list(REFS_ASSERT_COMPLETION),
                        details={
                            "trace_id": trace_or_calls.trace_id,
                            "span_name": span.name,
                            "status_message": status_msg,
                            "ordered_sequence": _tool_names_from_trace(trace_or_calls),
                            "constraint": "tool spans must not have ERROR status",
                            "expected_status_code": S.STATUS_OK,
                            "actual_status_code": span.status_code,
                        },
                    )
                )
        tn_for_pass = _tool_names_from_trace(trace_or_calls)
        return finish(
            AssertionResult(
                passed=True,
                assertion_name="assert_completion",
                tool=None,
                message=(
                    "assert_completion passed: no ERROR status on tool spans in trace "
                    f"(trace_id={trace_or_calls.trace_id!r})."
                ),
                regulatory_refs=list(REFS_ASSERT_COMPLETION),
                details={
                    "trace_id": trace_or_calls.trace_id,
                    "ordered_sequence": tn_for_pass,
                    "constraint": "tool spans must not have ERROR status",
                },
            )
        )

    ordered_names = [r.tool_name for r in trace_or_calls]
    for r in trace_or_calls:
        if r.error is not None:
            msg = f"assert_completion: tool {r.tool_name!r} failed: {r.error}"
            return finish(
                AssertionResult(
                    passed=False,
                    assertion_name="assert_completion",
                    tool=r.tool_name,
                    message=msg,
                    regulatory_refs=list(REFS_ASSERT_COMPLETION),
                    details={
                        "tool_call_id": r.tool_call_id,
                        "constraint": "ToolCallRecord.error must be None",
                        "expected_error": None,
                        "actual_error": r.error,
                        "ordered_sequence": ordered_names,
                    },
                )
            )
    return finish(
        AssertionResult(
            passed=True,
            assertion_name="assert_completion",
            tool=None,
            message="assert_completion passed: all tool call records have error=None.",
            regulatory_refs=list(REFS_ASSERT_COMPLETION),
            details={
                "record_count": len(trace_or_calls),
                "ordered_sequence": ordered_names,
                "constraint": "ToolCallRecord.error must be None",
            },
        )
    )


def assert_mutual_exclusion(
    trace_or_calls: Trace | Sequence[ToolCallRecord] | Sequence[str],
    tool_a: str,
    tool_b: str,
) -> AssertionResult:
    """Assert ``tool_a`` and ``tool_b`` are not both invoked in the same run.

    If either tool never appears, the check passes. Fails only when both have
    at least one call.
    """
    ordered = _ordered_tool_names(trace_or_calls)
    if ordered.count(tool_a) > 0 and ordered.count(tool_b) > 0:
        msg = (
            f"assert_mutual_exclusion: {tool_a!r} and {tool_b!r} must not both "
            f"be called; order seen: {ordered!r}"
        )
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_mutual_exclusion",
                tool=None,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_MUTUAL_EXCLUSION),
                details={
                    "tool_a": tool_a,
                    "tool_b": tool_b,
                    "ordered_sequence": ordered,
                    "constraint": "at most one of tool_a and tool_b may appear in the run",
                },
            )
        )
    ok_msg = (
        f"assert_mutual_exclusion passed: at most one of {tool_a!r} and {tool_b!r} "
        f"was called. order={ordered!r}"
    )
    return finish(
        AssertionResult(
            passed=True,
            assertion_name="assert_mutual_exclusion",
            tool=None,
            message=ok_msg,
            regulatory_refs=list(REFS_ASSERT_MUTUAL_EXCLUSION),
            details={
                "tool_a": tool_a,
                "tool_b": tool_b,
                "ordered_sequence": ordered,
                "constraint": "at most one of tool_a and tool_b may appear in the run",
            },
        )
    )
