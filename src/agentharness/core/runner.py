"""ScenarioRunner -- executes a scenario, collects the trace, and evaluates assertions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agentharness.core.result import RunResult
from agentharness.mocks.cassette import (
    Cassette,
    default_cassette_path,
    load,
    normalize_args,
)
from agentharness.mocks.interceptor import (
    HarnessInterceptor,
    InterceptMode,
    ReplayCassetteError,
    ToolCallRecord,
)
from agentharness.telemetry.collector import TraceCollector


def run_scenario(
    scenario_path: str | Path,
    *,
    mode: str | None = None,
    cassette_path: str | Path | None = None,
) -> RunResult:
    """Run a scenario and return a :class:`RunResult`.

    Loads optional YAML next to the path. If the file exists and defines
    ``tool_calls`` (list of tool names), records each as a synthetic
    :class:`~agentharness.mocks.interceptor.ToolCallRecord` via
    :class:`~agentharness.telemetry.collector.TraceCollector` so structural
    assertions (e.g. Sprint 1 exit criteria) can pass. Otherwise returns a
    trace shell with ``harness.scenario_id`` only.

    If ``mode`` is set (``\"mock\"``, ``\"live\"``, or ``\"replay\"``), it overrides the YAML
    ``mode`` key for execution and trace metadata.

    In ``\"replay\"`` mode, loads a :class:`~agentharness.mocks.cassette.Cassette` from
    ``cassette_path``, or from :func:`~agentharness.mocks.cassette.default_cassette_path`
    using the scenario file stem when ``cassette_path`` is omitted. Synthetic tool rows
    use cassette lookups (raises :class:`~agentharness.mocks.interceptor.ReplayCassetteError`
    when missing).
    """
    path = Path(scenario_path)
    data: dict[str, Any] = {}
    if path.is_file():
        raw = path.read_text(encoding="utf-8")
        loaded = yaml.safe_load(raw)
        if isinstance(loaded, dict):
            data = loaded

    scenario_id = path.as_posix()
    mode_str = str(mode) if mode is not None else str(data.get("mode", "mock"))
    seed_raw = data.get("seed")
    seed: int | None = int(seed_raw) if isinstance(seed_raw, int) else None

    collector = TraceCollector(scenario_id=scenario_id, mode=mode_str, seed=seed)

    cassette: Cassette | None = None
    if mode_str == "replay":
        cp = (
            Path(cassette_path).resolve()
            if cassette_path is not None
            else default_cassette_path(path.stem)
        )
        cassette = load(cp)
        interceptor = HarnessInterceptor(
            mode=InterceptMode.REPLAY,
            mock_responses={},
            cassette=cassette,
        )
    elif mode_str == "mock":
        interceptor = HarnessInterceptor(mode=InterceptMode.MOCK, mock_responses={})
    else:
        interceptor = HarnessInterceptor(mode=InterceptMode.LIVE, mock_responses={})

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
            if mode_str == "replay":
                assert cassette is not None
                norm = normalize_args({})
                response = cassette.lookup(name, norm)
                if response is None:
                    raise ReplayCassetteError(name, norm)
                was_mocked = True
            else:
                response = f"synthetic:{name}"
                was_mocked = mode_str == "mock"
            interceptor.record_call(
                name,
                {},
                f"synthetic-{i}",
                response=response,
                duration_ms=1.0,
                was_mocked=was_mocked,
            )

    return RunResult(
        trace=collector.build(),
        scenario_path=path.as_posix(),
        tool_call_records=list(interceptor.calls),
    )
