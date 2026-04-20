"""Run example scenarios: LangGraph ``ToolNode`` + interceptor, or core ``run_scenario`` fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from langgraph.runtime import Runtime

from agentharness.adapters.langgraph import create_intercepted_tool_node
from agentharness.core.result import RunResult
from agentharness.core.runner import run_scenario
from agentharness.mocks.interceptor import HarnessInterceptor, InterceptMode, ToolCallRecord
from agentharness.telemetry import schema as S
from agentharness.telemetry.collector import TraceCollector

from .refund_tools import ALL_REFUND_TOOLS


def _runtime_config() -> dict[str, Any]:
    return {"configurable": {"__pregel_runtime": Runtime()}}


def _tool_call(
    name: str,
    args: dict[str, Any],
    call_id: str,
) -> list[dict[str, Any]]:
    return [{"name": name, "args": args, "id": call_id, "type": "tool_call"}]


def _default_mock_registry(overrides: Any) -> dict[str, str]:
    base: dict[str, str] = {
        "lookup_order": '{"status":"ok"}',
        "check_refund_eligibility": '{"eligible":true}',
        "calculate_refund": '{"amount":50.0}',
        "request_approval": '{"approval_id":"APR-DEFAULT"}',
        "issue_refund": '{"status":"mocked"}',
        "escalate_to_human": '{"status":"escalated"}',
    }
    if isinstance(overrides, dict):
        for k, v in overrides.items():
            if isinstance(k, str) and isinstance(v, str):
                base[k] = v
    return base


def run_example_scenario(scenario_path: str | Path) -> RunResult:
    """Load YAML; if ``steps`` is present, execute tools via LangGraph ``ToolNode`` (mock)."""
    path = Path(scenario_path)
    if not path.is_file():
        msg = f"scenario file not found: {path}"
        raise FileNotFoundError(msg)
    raw = path.read_text(encoding="utf-8")
    data: Any = yaml.safe_load(raw)
    if not isinstance(data, dict) or "steps" not in data:
        return run_scenario(path)

    steps = data["steps"]
    if not isinstance(steps, list):
        raise ValueError("steps must be a list")

    mocks = _default_mock_registry(data.get("mock_responses"))
    interceptor = HarnessInterceptor(
        mode=InterceptMode.MOCK,
        mock_responses=mocks,
    )

    scenario_id = data.get("scenario_id")
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        scenario_id = path.as_posix()

    collector = TraceCollector(scenario_id=scenario_id, mode="mock", seed=None)
    orig = interceptor.record_call

    def wrapped(*args: Any, **kwargs: Any) -> ToolCallRecord:
        rec = orig(*args, **kwargs)
        collector.record(rec)
        return rec

    interceptor.record_call = wrapped  # type: ignore[method-assign]

    tool_node = create_intercepted_tool_node(ALL_REFUND_TOOLS, interceptor)
    cfg = _runtime_config()

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"steps[{i}] must be a mapping")
        name = step.get("tool")
        if not isinstance(name, str):
            raise ValueError(f"steps[{i}].tool must be a string")
        args = step.get("args") or {}
        if not isinstance(args, dict):
            raise ValueError(f"steps[{i}].args must be a mapping when present")
        tool_node.invoke(_tool_call(name, args, f"call_{i}"), config=cfg)

    trace = collector.build()
    trace.attributes[S.HARNESS_MODE] = "mock"
    return RunResult(trace=trace, scenario_path=path.as_posix())
