"""``agentharness run`` — execute a scenario YAML and print :class:`AssertionResult` output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from agentharness.assertions.base import (
    AssertionResult,
    reset_results_collector,
    set_results_collector,
)
from agentharness.assertions.structural import assert_called_before
from agentharness.core.runner import run_scenario
from agentharness.core.trace import Trace
from agentharness.reporting.console import ConsoleReporter
from agentharness.telemetry import schema as S


def _load_scenario_yaml(path: Path) -> Any:
    """Parse scenario YAML (Phase 0: same shape as :func:`agentharness.core.runner.run_scenario`).

    The :mod:`agentharness.core.scenario` module will grow a typed Scenario model; until then the
    runner and CLI share the same YAML structure (``tool_calls``, optional ``assertions``).
    """
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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
    try:
        try:
            result = run_scenario(raw_path)
        except OSError as exc:
            sys.stderr.write(f"agentharness run: could not run scenario: {exc}\n")
            return 2

        result.trace.attributes[S.HARNESS_MODE] = str(args.mode)

        try:
            _run_yaml_assertions(data, result.trace)
        except AssertionError:
            pass  # ``finish`` already recorded the :class:`AssertionResult` on the list before raising
        except ValueError as exc:
            sys.stderr.write(f"agentharness run: invalid scenario content: {exc}\n")
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

    if failures:
        return 1
    return 0
