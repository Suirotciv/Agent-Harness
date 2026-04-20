"""``agentharness record`` — run a scenario and write tool-call traffic to a cassette file."""

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
from agentharness.cli.run import _run_yaml_assertions
from agentharness.core.runner import run_scenario
from agentharness.mocks.cassette import (
    Cassette,
    CassetteEntry,
    default_cassette_path,
    make_cassette_key,
    normalize_args,
    save,
    utc_now_iso,
)
from agentharness.reporting.console import ConsoleReporter
from agentharness.telemetry import schema as S


def _load_scenario_yaml(path: Path) -> Any:
    """Parse scenario YAML (same shape as :func:`agentharness.cli.run.run_command`)."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def record_command(args: argparse.Namespace) -> int:
    """Execute ``agentharness record``; return process exit code (0 / 1 / 2)."""
    raw_path = Path(args.scenario)
    if not raw_path.is_file():
        sys.stderr.write(f"agentharness record: file not found: {raw_path}\n")
        return 2

    mode: str = args.mode
    if mode == "live" and not args.allow_real_tools:
        sys.stderr.write(
            "Live mode requires --allow-real-tools flag. This "
            "prevents accidental real tool calls. Pass "
            "--allow-real-tools to confirm.\n",
        )
        return 2

    if mode == "mock":
        sys.stderr.write(
            "WARNING: recording in mock mode captures mock "
            "responses, not real tool behavior. Pass --mode live "
            "to record real tool responses.\n",
        )

    if args.allow_sensitive_recording:
        sys.stderr.write(
            "WARNING: PII scrubbing is disabled. The cassette "
            "may contain personally identifiable information. "
            "Do not commit to version control without review.\n",
        )

    try:
        loaded = _load_scenario_yaml(raw_path)
    except yaml.YAMLError as exc:
        sys.stderr.write(f"agentharness record: invalid YAML: {exc}\n")
        return 2
    except OSError as exc:
        sys.stderr.write(f"agentharness record: could not read file: {exc}\n")
        return 2

    if loaded is not None and not isinstance(loaded, dict):
        sys.stderr.write("agentharness record: scenario root must be a mapping\n")
        return 2

    data: dict[str, Any] = loaded if isinstance(loaded, dict) else {}

    if args.output is not None:
        out_path = Path(args.output).resolve()
    else:
        out_path = default_cassette_path(raw_path.stem).resolve()

    collected: list[AssertionResult] = []
    tok = set_results_collector(collected)
    try:
        try:
            result = run_scenario(raw_path, mode=mode)
        except OSError as exc:
            sys.stderr.write(f"agentharness record: could not run scenario: {exc}\n")
            return 2

        result.trace.attributes[S.HARNESS_MODE] = str(mode)

        try:
            _run_yaml_assertions(data, result.trace)
        except AssertionError:
            pass
        except ValueError as exc:
            sys.stderr.write(f"agentharness record: invalid scenario content: {exc}\n")
            return 2
    finally:
        reset_results_collector(tok)

    assertion_results = collected
    failures = [r for r in assertion_results if not r.passed]
    if failures:
        cr = ConsoleReporter(failures)
        block = cr.render_failures()
        if block.strip():
            sys.stdout.write(block)
            if not block.endswith("\n"):
                sys.stdout.write("\n")
        summary = ConsoleReporter.summary_line(
            assertion_results,
            configuration_errors=0,
        )
        sys.stdout.write(summary + "\n")
        return 1

    pii_scrubbed = not bool(args.allow_sensitive_recording)
    created_at = utc_now_iso()
    entries: list[CassetteEntry] = []
    for rec in result.tool_call_records:
        args_norm = normalize_args(rec.args)
        key = make_cassette_key(rec.tool_name, args_norm)
        if rec.error is not None:
            response: Any = {"error": rec.error}
        else:
            response = rec.response
        entries.append(
            CassetteEntry(
                key=key,
                tool_name=rec.tool_name,
                args_normalized=args_norm,
                response=response,
                recorded_at=created_at,
            ),
        )

    cassette = Cassette(
        scenario_id=raw_path.as_posix(),
        created_at=created_at,
        mode="record",
        entries=entries,
        secrets_scrubbed=True,
        pii_scrubbed=pii_scrubbed,
    )
    written = save(cassette, out_path)
    sys.stdout.write(
        f"Cassette saved to {written} ({len(entries)} entries)\n",
    )
    return 0
