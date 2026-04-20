"""``agentharness run`` — execute a scenario YAML and print :class:`AssertionResult` output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

import yaml

from agentharness.assertions.base import (
    AssertionResult,
    reset_results_collector,
    set_results_collector,
)
from agentharness.assertions.structural import assert_called_before
from agentharness.core.result import RunResult
from agentharness.core.runner import run_scenario
from agentharness.core.trace import Trace
from agentharness.mocks.interceptor import ReplayCassetteError
from agentharness.reporting.console import ConsoleReporter
from agentharness.telemetry import schema as S


def _load_scenario_yaml(path: Path) -> Any:
    """Parse scenario YAML (Phase 0: same shape as :func:`agentharness.core.runner.run_scenario`).

    The :mod:`agentharness.core.scenario` module will grow a typed Scenario model; until then the
    runner and CLI share the same YAML structure (``tool_calls``, optional ``assertions``).
    """
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_baseline_trace(path: Path) -> Trace:
    """Load a baseline trace from a cassette ``.json`` or trace ``.jsonl`` file."""
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        from agentharness.telemetry.jsonl import iter_traces_jsonl

        first = next(iter(iter_traces_jsonl(path)), None)
        if first is None:
            msg = f"no trace lines in {path}"
            raise ValueError(msg)
        return first
    if suffix == ".json":
        from agentharness.mocks.cassette import load as load_cassette
        from agentharness.reporting.diff import trace_from_cassette

        return trace_from_cassette(load_cassette(path))
    msg = f"unsupported baseline trace format (use .json cassette or .jsonl): {path}"
    raise ValueError(msg)


def _run_yaml_assertions(data: dict[str, Any], trace: Trace) -> None:
    """Evaluate YAML ``assertions`` using harness helpers (results captured via :func:`finish`)."""
    specs = data.get("assertions")
    if specs is None:
        return
    if not isinstance(specs, list):
        raise ValueError("assertions must be a list")

    for i, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise ValueError(f"assertions[{i}] must be a mapping")
        kind = spec.get("kind")
        if kind == "called_before":
            earlier = spec.get("earlier")
            later = spec.get("later")
            if not isinstance(earlier, str) or not isinstance(later, str):
                raise ValueError("called_before requires string earlier and later")
            assert_called_before(trace, earlier, later)
        else:
            raise ValueError(f"unsupported assertion kind: {kind!r}")


def run_command(args: argparse.Namespace) -> int:
    """Execute ``agentharness run``; return process exit code (0 / 1 / 2)."""
    raw_path = Path(args.scenario)
    if not raw_path.is_file():
        sys.stderr.write(f"agentharness run: file not found: {raw_path}\n")
        return 2

    try:
        loaded = _load_scenario_yaml(raw_path)
    except yaml.YAMLError as exc:
        sys.stderr.write(f"agentharness run: invalid YAML: {exc}\n")
        return 2
    except OSError as exc:
        sys.stderr.write(f"agentharness run: could not read file: {exc}\n")
        return 2

    if loaded is not None and not isinstance(loaded, dict):
        sys.stderr.write("agentharness run: scenario root must be a mapping\n")
        return 2

    data: dict[str, Any] = loaded if isinstance(loaded, dict) else {}

    collected: list[AssertionResult] = []
    tok = set_results_collector(collected)
    result: RunResult | None = None
    try:
        try:
            replay_arg = getattr(args, "replay", None)
            if replay_arg is not None:
                if "--mode" in sys.argv:
                    sys.stderr.write(
                        "WARNING: --mode is ignored when --replay is set. "
                        "Replay mode is always used with a cassette.\n",
                    )
                cassette_kw = Path(replay_arg).resolve() if replay_arg else None
                result = run_scenario(
                    raw_path,
                    mode="replay",
                    cassette_path=cassette_kw,
                )
                result.trace.attributes[S.HARNESS_MODE] = "replay"
            else:
                result = run_scenario(raw_path, mode=str(args.mode))
                result.trace.attributes[S.HARNESS_MODE] = str(args.mode)

            try:
                _run_yaml_assertions(data, result.trace)
            except AssertionError:
                pass  # ``finish`` already recorded the :class:`AssertionResult` on the list before raising
            except ValueError as exc:
                sys.stderr.write(f"agentharness run: invalid scenario content: {exc}\n")
                return 2
        except ReplayCassetteError as exc:
            sys.stderr.write(f"{exc}\n")
            return 2
        except FileNotFoundError as exc:
            sys.stderr.write(f"agentharness run: cassette not found: {exc}\n")
            return 2
        except OSError as exc:
            sys.stderr.write(f"agentharness run: could not run scenario: {exc}\n")
            return 2
    finally:
        reset_results_collector(tok)

    assertion_results = collected

    failures = [r for r in assertion_results if not r.passed]
    cr = ConsoleReporter(failures)
    block = cr.render_failures()
    if block.strip():
        sys.stdout.write(block)
        if not block.endswith("\n"):
            sys.stdout.write("\n")
    summary = ConsoleReporter.summary_line(assertion_results, configuration_errors=0)
    sys.stdout.write(summary + "\n")

    diff_arg = getattr(args, "diff", None)
    if diff_arg is not None:
        assert result is not None
        from agentharness.reporting.diff import DiffMode, diff_traces, format_diff

        try:
            baseline = _load_baseline_trace(Path(diff_arg).resolve())
        except (ValueError, OSError, FileNotFoundError) as exc:
            sys.stderr.write(
                f"agentharness run: could not load baseline trace: {exc}\n",
            )
            return 2
        mode = cast(DiffMode, getattr(args, "diff_mode", "strict"))
        td = diff_traces(baseline, result.trace, mode=mode)
        sys.stdout.write(format_diff(td) + "\n")

    if failures:
        return 1
    return 0
