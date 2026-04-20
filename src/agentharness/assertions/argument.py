"""Argument assertions (Tests 2.1-2.4).

assert_arg_lte, assert_arg_pattern, assert_arg_schema, assert_arg_not_contains.
Verifies the agent called tools with correct parameters.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any, cast

import jsonschema

from agentharness.assertions.base import (
    REFS_ASSERT_ARG_LTE,
    REFS_ASSERT_ARG_NOT_CONTAINS,
    REFS_ASSERT_ARG_PATTERN,
    REFS_ASSERT_ARG_SCHEMA,
    AssertionResult,
    finish,
)
from agentharness.assertions.structural import _span_tool_name
from agentharness.core.trace import Span, Trace
from agentharness.mocks.interceptor import ToolCallRecord
from agentharness.telemetry import schema as S


def _args_from_span(span: Span) -> dict[str, Any]:
    raw = span.attributes.get(S.INPUT_VALUE)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return cast(dict[str, Any], json.loads(raw))
        except json.JSONDecodeError:
            return {}
    return {}


def _args_dicts_for_tool(
    trace_or_calls: Trace | Sequence[ToolCallRecord],
    tool: str,
) -> list[dict[str, Any]]:
    """Collect ``args`` dicts for every invocation of ``tool`` in order."""
    if isinstance(trace_or_calls, Trace):
        out: list[dict[str, Any]] = []
        for span in trace_or_calls.spans:
            if _span_tool_name(span) != tool:
                continue
            out.append(_args_from_span(span))
        return out
    return [r.args for r in trace_or_calls if r.tool_name == tool]


def assert_arg_lte(
    trace_or_calls: Trace | Sequence[ToolCallRecord],
    *,
    tool: str,
    arg: str,
    value: float | int,
) -> AssertionResult:
    """Assert every call to ``tool`` passes ``args[arg] <= value`` (numeric)."""
    calls = _args_dicts_for_tool(trace_or_calls, tool)
    if not calls:
        msg = f"assert_arg_lte: tool {tool!r} was never called, cannot check {arg!r}"
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_arg_lte",
                tool=tool,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_ARG_LTE),
                details={
                    "tool": tool,
                    "arg": arg,
                    "limit": value,
                    "constraint": "args[arg] must be numeric and <= limit for every call",
                    "actual_calls": 0,
                },
            )
        )
    limit = float(value)
    for i, ad in enumerate(calls):
        if arg not in ad:
            msg = f"assert_arg_lte: call {i} to {tool!r} has no {arg!r} in args {ad!r}"
            return finish(
                AssertionResult(
                    passed=False,
                    assertion_name="assert_arg_lte",
                    tool=tool,
                    message=msg,
                    regulatory_refs=list(REFS_ASSERT_ARG_LTE),
                    details={
                        "tool": tool,
                        "call_index": i,
                        "arg": arg,
                        "limit": limit,
                        "args": ad,
                        "constraint": "args[arg] must be numeric and <= limit for every call",
                    },
                )
            )
        cur = ad[arg]
        if not isinstance(cur, (int, float)):
            msg = f"assert_arg_lte: {arg!r} must be numeric, got {type(cur).__name__}"
            return finish(
                AssertionResult(
                    passed=False,
                    assertion_name="assert_arg_lte",
                    tool=tool,
                    message=msg,
                    regulatory_refs=list(REFS_ASSERT_ARG_LTE),
                    details={
                        "tool": tool,
                        "call_index": i,
                        "arg": arg,
                        "limit": limit,
                        "actual_value": cur,
                        "actual_type": type(cur).__name__,
                        "constraint": "args[arg] must be numeric and <= limit for every call",
                    },
                )
            )
        if float(cur) > limit:
            msg = f"assert_arg_lte: {arg}={cur!r} exceeds {value!r} (call {i} to {tool!r})"
            return finish(
                AssertionResult(
                    passed=False,
                    assertion_name="assert_arg_lte",
                    tool=tool,
                    message=msg,
                    regulatory_refs=list(REFS_ASSERT_ARG_LTE),
                    details={
                        "tool": tool,
                        "call_index": i,
                        "arg": arg,
                        "limit": value,
                        "actual_value": cur,
                        "constraint": "args[arg] must be numeric and <= limit for every call",
                    },
                )
            )
    ok_msg = (
        f"assert_arg_lte passed: every call to {tool!r} has {arg!r} <= {value!r} "
        f"({len(calls)} call(s))."
    )
    return finish(
        AssertionResult(
            passed=True,
            assertion_name="assert_arg_lte",
            tool=tool,
            message=ok_msg,
            regulatory_refs=list(REFS_ASSERT_ARG_LTE),
            details={
                "tool": tool,
                "arg": arg,
                "limit": value,
                "call_count": len(calls),
                "constraint": "args[arg] must be numeric and <= limit for every call",
            },
        )
    )


def assert_arg_pattern(
    trace_or_calls: Trace | Sequence[ToolCallRecord],
    *,
    tool: str,
    arg: str,
    pattern: str,
) -> AssertionResult:
    """Assert ``args[arg]`` as a string matches the regex ``pattern`` (``re.search``)."""
    calls = _args_dicts_for_tool(trace_or_calls, tool)
    if not calls:
        msg = f"assert_arg_pattern: tool {tool!r} was never called, cannot check {arg!r}"
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_arg_pattern",
                tool=tool,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_ARG_PATTERN),
                details={
                    "tool": tool,
                    "arg": arg,
                    "pattern": pattern,
                    "constraint": "str(args[arg]) must match regex pattern for every call",
                    "actual_calls": 0,
                },
            )
        )
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"assert_arg_pattern: invalid regex: {exc}") from exc
    for i, ad in enumerate(calls):
        if arg not in ad:
            msg = f"assert_arg_pattern: call {i} to {tool!r} has no {arg!r}"
            return finish(
                AssertionResult(
                    passed=False,
                    assertion_name="assert_arg_pattern",
                    tool=tool,
                    message=msg,
                    regulatory_refs=list(REFS_ASSERT_ARG_PATTERN),
                    details={
                        "tool": tool,
                        "call_index": i,
                        "arg": arg,
                        "pattern": pattern,
                        "constraint": "str(args[arg]) must match regex pattern for every call",
                    },
                )
            )
        text = str(ad[arg])
        if rx.search(text) is None:
            msg = (
                f"assert_arg_pattern: {arg!r}={text!r} does not match {pattern!r} "
                f"(call {i} to {tool!r})"
            )
            return finish(
                AssertionResult(
                    passed=False,
                    assertion_name="assert_arg_pattern",
                    tool=tool,
                    message=msg,
                    regulatory_refs=list(REFS_ASSERT_ARG_PATTERN),
                    details={
                        "tool": tool,
                        "call_index": i,
                        "arg": arg,
                        "pattern": pattern,
                        "actual_value": text,
                        "constraint": "str(args[arg]) must match regex pattern for every call",
                    },
                )
            )
    ok_msg = (
        f"assert_arg_pattern passed: {arg!r} matches {pattern!r} on all {len(calls)} "
        f"call(s) to {tool!r}."
    )
    return finish(
        AssertionResult(
            passed=True,
            assertion_name="assert_arg_pattern",
            tool=tool,
            message=ok_msg,
            regulatory_refs=list(REFS_ASSERT_ARG_PATTERN),
            details={
                "tool": tool,
                "arg": arg,
                "pattern": pattern,
                "call_count": len(calls),
                "constraint": "str(args[arg]) must match regex pattern for every call",
            },
        )
    )


def assert_arg_schema(
    trace_or_calls: Trace | Sequence[ToolCallRecord],
    *,
    tool: str,
    schema: Any,
) -> AssertionResult:
    """Assert each ``args`` payload for ``tool`` validates against JSON Schema ``schema``."""
    calls = _args_dicts_for_tool(trace_or_calls, tool)
    if not calls:
        msg = f"assert_arg_schema: tool {tool!r} was never called"
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_arg_schema",
                tool=tool,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_ARG_SCHEMA),
                details={
                    "tool": tool,
                    "constraint": "each args dict for tool must validate against JSON Schema",
                    "actual_calls": 0,
                },
            )
        )
    for i, ad in enumerate(calls):
        try:
            jsonschema.validate(instance=ad, schema=schema)
        except jsonschema.ValidationError as exc:
            msg = f"assert_arg_schema: call {i} to {tool!r} failed schema: {exc.message}"
            return finish(
                AssertionResult(
                    passed=False,
                    assertion_name="assert_arg_schema",
                    tool=tool,
                    message=msg,
                    regulatory_refs=list(REFS_ASSERT_ARG_SCHEMA),
                    details={
                        "tool": tool,
                        "call_index": i,
                        "instance": ad,
                        "schema_error": exc.message,
                        "constraint": "each args dict for tool must validate against JSON Schema",
                    },
                ),
                cause=exc,
            )
    ok_msg = (
        f"assert_arg_schema passed: all {len(calls)} call(s) to {tool!r} validate against schema."
    )
    return finish(
        AssertionResult(
            passed=True,
            assertion_name="assert_arg_schema",
            tool=tool,
            message=ok_msg,
            regulatory_refs=list(REFS_ASSERT_ARG_SCHEMA),
            details={
                "tool": tool,
                "call_count": len(calls),
                "constraint": "each args dict for tool must validate against JSON Schema",
            },
        )
    )


def assert_arg_not_contains(
    trace_or_calls: Trace | Sequence[ToolCallRecord],
    *,
    tool: str,
    arg: str,
    substring: str,
) -> AssertionResult:
    """Assert ``substring`` does not appear in ``str(args[arg])`` for any call to ``tool``."""
    calls = _args_dicts_for_tool(trace_or_calls, tool)
    if not calls:
        msg = f"assert_arg_not_contains: tool {tool!r} was never called"
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_arg_not_contains",
                tool=tool,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_ARG_NOT_CONTAINS),
                details={
                    "tool": tool,
                    "arg": arg,
                    "substring": substring,
                    "constraint": "substring must not appear in str(args[arg]) for any call",
                    "actual_calls": 0,
                },
            )
        )
    for i, ad in enumerate(calls):
        if arg not in ad:
            msg = f"assert_arg_not_contains: call {i} to {tool!r} has no {arg!r}"
            return finish(
                AssertionResult(
                    passed=False,
                    assertion_name="assert_arg_not_contains",
                    tool=tool,
                    message=msg,
                    regulatory_refs=list(REFS_ASSERT_ARG_NOT_CONTAINS),
                    details={
                        "tool": tool,
                        "call_index": i,
                        "arg": arg,
                        "substring": substring,
                        "constraint": "substring must not appear in str(args[arg]) for any call",
                    },
                )
            )
        text = str(ad[arg])
        if substring in text:
            msg = (
                f"assert_arg_not_contains: {arg!r} contains forbidden substring "
                f"{substring!r} (call {i} to {tool!r})"
            )
            return finish(
                AssertionResult(
                    passed=False,
                    assertion_name="assert_arg_not_contains",
                    tool=tool,
                    message=msg,
                    regulatory_refs=list(REFS_ASSERT_ARG_NOT_CONTAINS),
                    details={
                        "tool": tool,
                        "call_index": i,
                        "arg": arg,
                        "substring": substring,
                        "actual_value": text,
                        "constraint": "substring must not appear in str(args[arg]) for any call",
                    },
                )
            )
    ok_msg = (
        f"assert_arg_not_contains passed: {arg!r} omits {substring!r} on all "
        f"{len(calls)} call(s) to {tool!r}."
    )
    return finish(
        AssertionResult(
            passed=True,
            assertion_name="assert_arg_not_contains",
            tool=tool,
            message=ok_msg,
            regulatory_refs=list(REFS_ASSERT_ARG_NOT_CONTAINS),
            details={
                "tool": tool,
                "arg": arg,
                "substring": substring,
                "call_count": len(calls),
                "constraint": "substring must not appear in str(args[arg]) for any call",
            },
        )
    )
