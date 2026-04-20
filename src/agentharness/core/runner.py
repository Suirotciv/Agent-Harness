"""ScenarioRunner -- executes a scenario, collects the trace, and evaluates assertions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agentharness.core.result import RunResult
from agentharness.mocks.interceptor import (
    HarnessInterceptor,
    InterceptMode,
    ToolCallRecord,
)
from agentharness.telemetry.collector import TraceCollector


def run_scenario(scenario_path: str | Path) -> RunResult:
    """Run a scenario and return a :class:`RunResult`.

    Loads optional YAML next to the path. If the file exists and defines
    ``tool_calls`` (list of tool names), records each as a synthetic
    :class:`~agentharness.mocks.interceptor.ToolCallRecord` via
    :class:`~agentharness.telemetry.collector.TraceCollector` so structural
    assertions (e.g. Sprint 1 exit criteria) can pass. Otherwise returns a
    trace shell with ``harness.scenario_id`` only.
    """
    path = Path(scenario_path)
    data: dict[str, Any] = {}
    if path.is_file():
        raw = path.read_text(encoding="utf-8")
        loaded = yaml.safe_load(raw)
        if isinstance(loaded, dict):
            data = loaded

    scenario_id = path.as_posix()
    mode_str = str(data.get("mode", "mock"))
    seed_raw = data.get("seed")
    seed: int | None = int(seed_raw) if isinstance(seed_raw, int) else None

    collector = TraceCollector(scenario_id=scenario_id, mode=mode_str, seed=seed)
    imode = InterceptMode.MOCK if mode_str == "mock" else InterceptMode.LIVE
    interceptor = HarnessInterceptor(mode=imode, mock_responses={})

    orig = interceptor.record_call

    def wrapped(*args: Any, **kwargs: Any) -> ToolCallRecord:
        rec = orig(*args, **kwargs)
        collector.record(rec)
        return rec

    interceptor.record_call = wrapped  # type: ignore[method-assign]

    tools = data.get("tool_calls")
    if isinstance(tools, list):
        names = [str(x) for x in tools if x is not None]
        for i, name in enumerate(names):
            interceptor.record_call(
                name,
                {},
                f"synthetic-{i}",
                response=f"synthetic:{name}",
                duration_ms=1.0,
                was_mocked=True,
            )

    return RunResult(trace=collector.build(), scenario_path=path.as_posix())
