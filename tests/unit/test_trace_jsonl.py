"""Unit tests for Trace JSONL serialization (AD-008)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agentharness.core.trace import Trace, new_trace_id
from agentharness.telemetry.jsonl import (
    default_trace_path,
    iter_traces_jsonl,
    parse_trace_jsonl_line,
    trace_to_jsonl_line,
    write_trace_jsonl,
    write_trace_to_default_location,
)


def test_trace_to_jsonl_line_roundtrip() -> None:
    t = Trace(trace_id=new_trace_id(), attributes={"harness.mode": "mock"})
    line = trace_to_jsonl_line(t)
    assert "\n" not in line
    t2 = parse_trace_jsonl_line(line)
    assert t2.trace_id == t.trace_id
    assert t2.attributes.get("harness.mode") == "mock"


def test_write_and_iter_traces_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "t.jsonl"
    a = Trace(trace_id=new_trace_id())
    b = Trace(trace_id=new_trace_id())
    write_trace_jsonl(p, a)
    write_trace_jsonl(p, b, append=True)
    traces = list(iter_traces_jsonl(p))
    assert len(traces) == 2
    assert traces[0].trace_id == a.trace_id
    assert traces[1].trace_id == b.trace_id


def test_default_trace_path_shape(tmp_path: Path) -> None:
    fixed = datetime(2026, 4, 19, 12, 30, 45, tzinfo=timezone.utc)
    path = default_trace_path("refund/happy", base_dir=tmp_path / "x", when=fixed)
    assert path == tmp_path / "x" / "2026-04-19" / "refund_happy_20260419T123045Z.jsonl"


def test_write_trace_to_default_location_under_tmp(tmp_path: Path) -> None:
    t = Trace(trace_id=new_trace_id())
    out = write_trace_to_default_location(t, "my_scenario", base_dir=tmp_path / "root", when=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    assert out.parent.name == "2026-01-02"
    assert out.name.startswith("my_scenario_")
    assert out.name.endswith(".jsonl")
    assert list(iter_traces_jsonl(out))[0].trace_id == t.trace_id
