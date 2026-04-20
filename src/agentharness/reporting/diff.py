"""Structural regression diff between two :class:`~agentharness.core.trace.Trace` objects.

Import **only** from ``agentharness.reporting.diff`` — this module is not re-exported from
:mod:`agentharness.reporting` (same pattern as :mod:`agentharness.reporting.console`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, cast

from agentharness.core.trace import (
    Span,
    SpanStatusCode,
    Trace,
    new_span_id,
    utc_now_unix_nano,
)
from agentharness.mocks.cassette import Cassette
from agentharness.telemetry import schema as S

DiffMode = Literal["strict", "subset", "superset"]


@dataclass(frozen=True)
class SpanDiff:
    """One detected difference between baseline and candidate tool-call traces."""

    kind: str
    tool_name: str
    detail: str


@dataclass(frozen=True)
class TraceDiff:
    """Result of comparing a baseline trace to a candidate trace."""

    baseline_scenario_id: str
    candidate_scenario_id: str
    span_diffs: list[SpanDiff]
    is_equivalent: bool


def _scenario_id(trace: Trace) -> str:
    raw = trace.attributes.get(S.HARNESS_SCENARIO_ID)
    return str(raw) if raw is not None else ""


def _tool_step_from_span(span: Span) -> tuple[str, str, str] | None:
    """Return ``(tool_name, normalized_input_json, status_code)`` for a TOOL span, else None."""
    kind = span.attributes.get(S.OPENINFERENCE_SPAN_KIND)
    if kind != S.SPAN_KIND_TOOL and span.kind != S.SPAN_KIND_TOOL:
        return None
    name = str(span.attributes.get(S.TOOL_NAME) or span.name)
    raw_in = span.attributes.get(S.INPUT_VALUE, "{}")
    if isinstance(raw_in, str):
        try:
            parsed: object = json.loads(raw_in)
        except json.JSONDecodeError:
            parsed = {}
    else:
        parsed = raw_in
    norm = json.dumps(parsed, sort_keys=True, ensure_ascii=False, default=str)
    status = str(span.status_code)
    return (name, norm, status)


def extract_tool_steps(trace: Trace) -> list[tuple[str, str, str]]:
    """Ordered TOOL spans: ``(tool_name, input_json_normalized, status_code)``."""
    out: list[tuple[str, str, str]] = []
    for span in trace.spans:
        step = _tool_step_from_span(span)
        if step is not None:
            out.append(step)
    return out


def trace_from_cassette(cassette: Cassette) -> Trace:
    """Build a synthetic :class:`Trace` from cassette entries (order preserved)."""
    t = Trace()
    t.attributes[S.HARNESS_SCENARIO_ID] = cassette.scenario_id
    t.attributes[S.HARNESS_MODE] = "replay"
    now = utc_now_unix_nano()
    for entry in cassette.entries:
        err = (
            isinstance(entry.response, dict) and entry.response.get("error") is not None
        )
        status = cast(
            SpanStatusCode,
            S.STATUS_ERROR if err else S.STATUS_OK,
        )
        inp = json.dumps(entry.args_normalized, sort_keys=True, ensure_ascii=False)
        out_val = json.dumps(entry.response, default=str)
        span = Span(
            trace_id=t.trace_id,
            span_id=new_span_id(),
            name=entry.tool_name,
            kind=S.SPAN_KIND_TOOL,
            start_time_unix_nano=now,
            end_time_unix_nano=now,
            status_code=status,
            status_message=str(entry.response.get("error"))
            if isinstance(entry.response, dict) and entry.response.get("error")
            else None,
            attributes={
                S.OPENINFERENCE_SPAN_KIND: S.SPAN_KIND_TOOL,
                S.TOOL_NAME: entry.tool_name,
                S.INPUT_VALUE: inp,
                S.OUTPUT_VALUE: out_val,
            },
        )
        t.add_span(span)
    return t


def diff_traces(
    baseline: Trace,
    candidate: Trace,
    *,
    mode: DiffMode = "strict",
) -> TraceDiff:
    """Compare two traces and return a :class:`TraceDiff`.

    Tool steps are TOOL spans in order. Arguments are compared via normalized JSON
    (``sort_keys=True``) so key order does not affect equivalence.
    """
    b = extract_tool_steps(baseline)
    c = extract_tool_steps(candidate)
    bid = _scenario_id(baseline)
    cid = _scenario_id(candidate)

    if mode == "strict":
        diffs = _diff_strict(b, c)
    elif mode == "subset":
        diffs = _diff_subset(b, c)
    else:
        diffs = _diff_superset(b, c)

    return TraceDiff(
        baseline_scenario_id=bid,
        candidate_scenario_id=cid,
        span_diffs=diffs,
        is_equivalent=len(diffs) == 0,
    )


def _diff_strict(
    b: list[tuple[str, str, str]],
    c: list[tuple[str, str, str]],
) -> list[SpanDiff]:
    diffs: list[SpanDiff] = []
    n = max(len(b), len(c))
    for i in range(n):
        if i >= len(b):
            ct, _, _ = c[i]
            diffs.append(
                SpanDiff(
                    kind="added",
                    tool_name=ct,
                    detail=(
                        f"Extra tool call at candidate index {i}: {ct!r} "
                        "(no matching baseline step at this position)."
                    ),
                )
            )
            continue
        if i >= len(c):
            bt, _, _ = b[i]
            diffs.append(
                SpanDiff(
                    kind="removed",
                    tool_name=bt,
                    detail=(
                        f"Missing tool call at candidate index {i}: baseline has {bt!r}."
                    ),
                )
            )
            continue
        bt, ba, bs = b[i]
        ct, ca, cs = c[i]
        if bt != ct:
            diffs.append(
                SpanDiff(
                    kind="reordered",
                    tool_name=ct,
                    detail=(
                        f"At step {i}, baseline tool {bt!r} but candidate tool {ct!r} "
                        f"(sequence mismatch)."
                    ),
                )
            )
        elif ba != ca:
            diffs.append(
                SpanDiff(
                    kind="arg_changed",
                    tool_name=bt,
                    detail=(
                        f"At step {i} ({bt!r}), tool arguments differ "
                        f"(normalized JSON mismatch)."
                    ),
                )
            )
        elif bs != cs:
            diffs.append(
                SpanDiff(
                    kind="status_changed",
                    tool_name=bt,
                    detail=(f"At step {i} ({bt!r}), span status {bs!r} vs {cs!r}."),
                )
            )
    return diffs


def _diff_subset(
    b: list[tuple[str, str, str]],
    c: list[tuple[str, str, str]],
) -> list[SpanDiff]:
    """Baseline must occur as a subsequence of candidate (extra candidate steps allowed)."""
    diffs: list[SpanDiff] = []
    j = 0
    for i, bstep in enumerate(b):
        while j < len(c) and c[j] != bstep:
            j += 1
        if j >= len(c):
            bt, _, _ = bstep
            diffs.append(
                SpanDiff(
                    kind="removed",
                    tool_name=bt,
                    detail=(
                        f"Baseline step {i} ({bt!r}) not found in candidate "
                        "in the same relative order (subset match failed)."
                    ),
                )
            )
            return diffs
        j += 1
    return diffs


def _diff_superset(
    b: list[tuple[str, str, str]],
    c: list[tuple[str, str, str]],
) -> list[SpanDiff]:
    """Candidate must occur as a subsequence of baseline (fewer candidate steps allowed)."""
    diffs: list[SpanDiff] = []
    i = 0
    for j, cstep in enumerate(c):
        while i < len(b) and b[i] != cstep:
            i += 1
        if i >= len(b):
            ct, _, _ = cstep
            diffs.append(
                SpanDiff(
                    kind="added",
                    tool_name=ct,
                    detail=(
                        f"Candidate step {j} ({ct!r}) has no matching baseline step "
                        "in order (tool not present in baseline trace as required)."
                    ),
                )
            )
            return diffs
        i += 1
    return diffs


def format_diff(diff: TraceDiff, *, color: bool = True) -> str:
    """Human-readable diff summary for the terminal (Rich if available, else plain)."""
    if diff.is_equivalent:
        return "Traces are equivalent."

    lines = [f"{d.kind}: {d.detail}" for d in diff.span_diffs]

    if color:
        try:
            from rich.console import Console
            from rich.text import Text

            console = Console(color_system="standard", width=100)
            with console.capture() as cap:
                for d in diff.span_diffs:
                    style = {
                        "added": "green",
                        "removed": "red",
                        "reordered": "yellow",
                        "arg_changed": "magenta",
                        "status_changed": "cyan",
                    }.get(d.kind, "white")
                    console.print(Text(f"{d.kind}: {d.detail}", style=style))
            return cap.get().rstrip("\n")
        except Exception:
            pass

    return "\n".join(lines)
