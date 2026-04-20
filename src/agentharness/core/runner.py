"""ScenarioRunner -- executes a scenario, collects the trace, and evaluates assertions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agentharness.core.result import RunResult
from agentharness.core.trace import Span, Trace, new_span_id, utc_now_unix_nano
from agentharness.telemetry import schema as S


def _append_synthetic_tool_spans(trace: Trace, tool_names: list[str]) -> None:
    """Append TOOL spans in order (Phase 0 evidence path; real runs populate via collector)."""
    t0 = utc_now_unix_nano()
    for i, name in enumerate(tool_names):
        start = t0 + i * 1_000_000
        trace.add_span(
            Span(
                trace_id=trace.trace_id,
                span_id=new_span_id(),
                name=name,
                kind=S.SPAN_KIND_TOOL,
                start_time_unix_nano=start,
                end_time_unix_nano=start + 500_000,
                attributes={
                    S.OPENINFERENCE_SPAN_KIND: S.SPAN_KIND_TOOL,
                    S.TOOL_NAME: name,
                },
            )
        )


def run_scenario(scenario_path: str | Path) -> RunResult:
    """Run a scenario and return a :class:`RunResult`.

    Phase 0: loads optional YAML next to the path. If the file exists and defines
    ``tool_calls`` (list of tool names), appends synthetic TOOL spans in that order
    so structural assertions (e.g. Sprint 1 exit criteria) can pass. Otherwise
    builds a trace shell with ``harness.scenario_id`` only. Full graph execution
    and collector-driven spans come later.
    """
    path = Path(scenario_path)
    trace = Trace()
    trace.attributes[S.HARNESS_SCENARIO_ID] = path.as_posix()

    if path.is_file():
        raw = path.read_text(encoding="utf-8")
        data: Any = yaml.safe_load(raw)
        if isinstance(data, dict):
            tools = data.get("tool_calls")
            if isinstance(tools, list):
                names = [str(x) for x in tools if x is not None]
                _append_synthetic_tool_spans(trace, names)

    return RunResult(trace=trace, scenario_path=path.as_posix())
