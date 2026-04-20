"""Unit tests for :mod:`agentharness.reporting.diff` and CLI ``--diff``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from agentharness.core.trace import Span, Trace, new_span_id, new_trace_id, utc_now_unix_nano
from agentharness.mocks.cassette import (
    Cassette,
    CassetteEntry,
    make_cassette_key,
    save,
    utc_now_iso,
)
from agentharness.reporting.diff import (
    diff_traces,
    format_diff,
    trace_from_cassette,
)
from agentharness.telemetry import schema as S


def _tool_span(
    trace_id: str,
    name: str,
    args: dict[str, object],
    *,
    status: str = S.STATUS_OK,
) -> Span:
    return Span(
        trace_id=trace_id,
        span_id=new_span_id(),
        name=name,
        kind=S.SPAN_KIND_TOOL,
        start_time_unix_nano=utc_now_unix_nano(),
        status_code=status,  # type: ignore[arg-type]
        attributes={
            S.OPENINFERENCE_SPAN_KIND: S.SPAN_KIND_TOOL,
            S.TOOL_NAME: name,
            S.INPUT_VALUE: json.dumps(args, sort_keys=True),
        },
    )


def _trace_with_tools(
    scenario_id: str,
    tools: list[tuple[str, dict[str, object], str]],
) -> Trace:
    tid = new_trace_id()
    return Trace(
        trace_id=tid,
        attributes={S.HARNESS_SCENARIO_ID: scenario_id},
        spans=[_tool_span(tid, n, a, status=s) for n, a, s in tools],
    )


def test_identical_traces_equivalent() -> None:
    a = _trace_with_tools(
        "s1",
        [("a", {"x": 1}, S.STATUS_OK), ("b", {}, S.STATUS_OK)],
    )
    b = _trace_with_tools(
        "s2",
        [("a", {"x": 1}, S.STATUS_OK), ("b", {}, S.STATUS_OK)],
    )
    d = diff_traces(a, b, mode="strict")
    assert d.is_equivalent
    assert d.span_diffs == []


def test_tool_added_strict() -> None:
    base = _trace_with_tools("b", [("a", {}, S.STATUS_OK)])
    cand = _trace_with_tools(
        "c",
        [("a", {}, S.STATUS_OK), ("b", {}, S.STATUS_OK)],
    )
    d = diff_traces(base, cand, mode="strict")
    assert not d.is_equivalent
    assert d.span_diffs[0].kind == "added"
    assert d.span_diffs[0].tool_name == "b"


def test_tool_removed_strict() -> None:
    base = _trace_with_tools(
        "b",
        [("a", {}, S.STATUS_OK), ("b", {}, S.STATUS_OK)],
    )
    cand = _trace_with_tools("c", [("a", {}, S.STATUS_OK)])
    d = diff_traces(base, cand, mode="strict")
    assert not d.is_equivalent
    assert d.span_diffs[0].kind == "removed"
    assert d.span_diffs[0].tool_name == "b"


def test_tool_reordered_strict() -> None:
    base = _trace_with_tools(
        "b",
        [("a", {}, S.STATUS_OK), ("b", {}, S.STATUS_OK)],
    )
    cand = _trace_with_tools(
        "c",
        [("b", {}, S.STATUS_OK), ("a", {}, S.STATUS_OK)],
    )
    d = diff_traces(base, cand, mode="strict")
    assert not d.is_equivalent
    kinds = [x.kind for x in d.span_diffs]
    assert "reordered" in kinds


def test_arg_changed_strict() -> None:
    base = _trace_with_tools("b", [("t", {"q": 1}, S.STATUS_OK)])
    cand = _trace_with_tools("c", [("t", {"q": 2}, S.STATUS_OK)])
    d = diff_traces(base, cand, mode="strict")
    assert not d.is_equivalent
    assert d.span_diffs[0].kind == "arg_changed"


def test_status_changed_strict() -> None:
    base = _trace_with_tools("b", [("t", {}, S.STATUS_OK)])
    cand = _trace_with_tools("c", [("t", {}, S.STATUS_ERROR)])
    d = diff_traces(base, cand, mode="strict")
    assert not d.is_equivalent
    assert d.span_diffs[0].kind == "status_changed"


def test_args_order_independent() -> None:
    base = _trace_with_tools("b", [("t", {"a": 1, "b": 2}, S.STATUS_OK)])
    cand = _trace_with_tools("c", [("t", {"b": 2, "a": 1}, S.STATUS_OK)])
    d = diff_traces(base, cand, mode="strict")
    assert d.is_equivalent


def test_subset_ignores_extra_in_candidate() -> None:
    base = _trace_with_tools("b", [("a", {}, S.STATUS_OK)])
    cand = _trace_with_tools(
        "c",
        [("x", {}, S.STATUS_OK), ("a", {}, S.STATUS_OK), ("y", {}, S.STATUS_OK)],
    )
    d = diff_traces(base, cand, mode="subset")
    assert d.is_equivalent


def test_superset_flags_new_tool_in_candidate() -> None:
    base = _trace_with_tools(
        "b",
        [("a", {}, S.STATUS_OK), ("b", {}, S.STATUS_OK)],
    )
    cand = _trace_with_tools(
        "c",
        [("a", {}, S.STATUS_OK), ("z", {}, S.STATUS_OK)],
    )
    d = diff_traces(base, cand, mode="superset")
    assert not d.is_equivalent
    assert d.span_diffs[0].kind == "added"
    assert d.span_diffs[0].tool_name == "z"


def test_format_diff_equivalent() -> None:
    a = _trace_with_tools("b", [("a", {}, S.STATUS_OK)])
    b = _trace_with_tools("c", [("a", {}, S.STATUS_OK)])
    d = diff_traces(a, b, mode="strict")
    assert format_diff(d, color=False) == "Traces are equivalent."


def test_format_diff_one_line_per_span_diff() -> None:
    base = _trace_with_tools("b", [("a", {}, S.STATUS_OK)])
    cand = _trace_with_tools(
        "c",
        [("a", {}, S.STATUS_OK), ("b", {}, S.STATUS_OK)],
    )
    d = diff_traces(base, cand, mode="strict")
    out = format_diff(d, color=False)
    lines = out.strip().split("\n")
    assert len(lines) == len(d.span_diffs)


def test_trace_from_cassette_roundtrip() -> None:
    key = make_cassette_key("tool_a", {})
    entry = CassetteEntry(
        key=key,
        tool_name="tool_a",
        args_normalized={},
        response={"ok": True},
        recorded_at=utc_now_iso(),
    )
    cas = Cassette(
        scenario_id="sc",
        created_at=utc_now_iso(),
        mode="mock",
        entries=[entry],
    )
    tr = trace_from_cassette(cas)
    assert len(tr.spans) == 1
    d = diff_traces(tr, tr, mode="strict")
    assert d.is_equivalent


def test_cli_diff_after_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from agentharness.cli.run import run_command

    scenario = tmp_path / "scenario.yaml"
    scenario.write_text("tool_calls:\n  - tool_a\n", encoding="utf-8")
    key = make_cassette_key("tool_a", {})
    entry = CassetteEntry(
        key=key,
        tool_name="tool_a",
        args_normalized={},
        response={"ok": True},
        recorded_at=utc_now_iso(),
    )
    cas = Cassette(
        scenario_id=str(scenario),
        created_at=utc_now_iso(),
        mode="mock",
        entries=[entry],
    )
    cassette_path = tmp_path / "base.json"
    save(cas, cassette_path)

    args = argparse.Namespace(
        scenario=str(scenario),
        mode="mock",
        replay=str(cassette_path),
        diff=str(cassette_path),
        diff_mode="strict",
    )
    code = run_command(args)
    assert code == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert any("Agent-Harness" in ln for ln in lines)
    assert "Traces are equivalent." in out